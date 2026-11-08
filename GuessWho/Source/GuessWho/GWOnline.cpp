#include "GWOnline.h"

#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformApplicationMisc.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Guid.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "SocketSubsystemEOS.h"
#include "Styling/CoreStyle.h"
#include "UObject/UObjectGlobals.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"

#if defined(EOS_PLATFORM_BASE_FILE_NAME)
#include EOS_PLATFORM_BASE_FILE_NAME
#endif
#include "eos_sdk.h"
#include "eos_connect.h"
#include "eos_sessions.h"

DEFINE_LOG_CATEGORY_STATIC(LogGWOnline, Log, All);

namespace
{
	const TCHAR* ManorMap = TEXT("/Game/GW/Maps/L_Manor");
	const char* AttrCode = "GWCODE";
	const char* Bucket = "GW:1";
	const double HostTimeout = 15.0;
	const double JoinTimeout = 25.0;
	const double SearchEvery = 2.0;
	const double CodeOnScreen = 180.0;
	const int32 MaxPlayers = 16;

	class FGWSocketUtils : public ISocketSubsystemEOSUtils
	{
	public:
		explicit FGWSocketUtils(UGWOnlineSubsystem* InOwner) : Owner(InOwner) {}
		virtual EOS_ProductUserId GetLocalUserId() override { return Owner.IsValid() ? (EOS_ProductUserId)Owner->GetLocalUser() : nullptr; }
		virtual FString GetSessionId() override { return Owner.IsValid() ? Owner->GetSessionName() : FString(); }
		virtual FName GetSubsystemInstanceName() override { return NAME_None; }
		virtual bool IsLoggedIn() override { return Owner.IsValid() && Owner->GetLocalUser() != nullptr; }
	private:
		TWeakObjectPtr<UGWOnlineSubsystem> Owner;
	};

	FString NewCode()
	{
		// no 0/O, 1/I/L: the code is read aloud over voice chat
		static const TCHAR Letters[] = TEXT("ABCDEFGHJKMNPQRSTUVWXYZ23456789");
		const FGuid Guid = FGuid::NewGuid();
		const uint32 Parts[6] = { Guid.A, Guid.B, Guid.C, Guid.D, Guid.A >> 11, Guid.C >> 11 };
		FString Out;
		for (uint32 Part : Parts)
		{
			Out.AppendChar(Letters[Part % (UE_ARRAY_COUNT(Letters) - 1)]);
		}
		return Out;
	}

	FString ResultText(EOS_EResult Result) { return UTF8_TO_TCHAR(EOS_EResult_ToString(Result)); }
}

void UGWOnlineSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	TickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UGWOnlineSubsystem::Tick), 0.25f);
	MapHandle = FCoreUObjectDelegates::PostLoadMapWithWorld.AddUObject(this, &UGWOnlineSubsystem::OnMapLoaded);

	// test hooks of Tools/qa/eos_test.ps1
	bFreshDevice = FParse::Param(FCommandLine::Get(), TEXT("GWEOSNewDevice"));
	bAutoHost = FParse::Param(FCommandLine::Get(), TEXT("GWEOSHost"));
	FParse::Value(FCommandLine::Get(), TEXT("GWEOSJoin="), AutoJoin);
	if (bAutoHost || !AutoJoin.IsEmpty())
	{
		AutoAt = FPlatformTime::Seconds() + 4.0;
	}
}

void UGWOnlineSubsystem::Deinitialize()
{
	FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
	FCoreUObjectDelegates::PostLoadMapWithWorld.Remove(MapHandle);
	DestroySession();
	if (Sockets.IsValid())
	{
		Sockets->Shutdown();
		Sockets.Reset();
	}
	if (Platform.IsValid() && AuthNotify != 0)
	{
		EOS_Connect_RemoveNotifyAuthExpiration(EOS_Platform_GetConnectInterface(*Platform), AuthNotify);
	}
	Platform.Reset();
	Super::Deinitialize();
}

bool UGWOnlineSubsystem::EnsurePlatform()
{
	if (Platform.IsValid())
	{
		return true;
	}
	FString ProductId, SandboxId, DeploymentId, ClientId, ClientSecret, EncryptionKey;
	GConfig->GetString(TEXT("GWEOS"), TEXT("ProductId"), ProductId, GEngineIni);
	GConfig->GetString(TEXT("GWEOS"), TEXT("SandboxId"), SandboxId, GEngineIni);
	GConfig->GetString(TEXT("GWEOS"), TEXT("DeploymentId"), DeploymentId, GEngineIni);
	GConfig->GetString(TEXT("GWEOS"), TEXT("ClientId"), ClientId, GEngineIni);
	GConfig->GetString(TEXT("GWEOS"), TEXT("ClientSecret"), ClientSecret, GEngineIni);
	// Not "EncryptionKey": Unreal strips keys with that name from packaged configs (IniKeyDenylist in BaseGame.ini)
	GConfig->GetString(TEXT("GWEOS"), TEXT("EosDataKey"), EncryptionKey, GEngineIni);
	if (ProductId.IsEmpty() || ClientId.IsEmpty())
	{
		UE_LOG(LogGWOnline, Warning, TEXT("GWEOS: identifiers missing from the engine config"));
		return false;
	}

	IEOSSDKManager* Manager = IEOSSDKManager::Get();
	if (!Manager)
	{
		UE_LOG(LogGWOnline, Warning, TEXT("GWEOS: no SDK manager"));
		return false;
	}
	if (!Manager->IsInitialized())
	{
		UE_LOG(LogGWOnline, Warning, TEXT("GWEOS: the EOS SDK is not initialized"));
		return false;
	}

	// two instances on one PC (test) must not share a cache
	FString Cache = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("EOSCache"));
	if (bFreshDevice)
	{
		Cache += FString::Printf(TEXT("_%u"), FPlatformProcess::GetCurrentProcessId());
	}
	const FTCHARToUTF8 ProductUtf8(*ProductId), SandboxUtf8(*SandboxId), DeploymentUtf8(*DeploymentId), ClientUtf8(*ClientId), SecretUtf8(*ClientSecret), KeyUtf8(*EncryptionKey), CacheUtf8(*Cache);

	EOS_Platform_Options Options = {};
	Options.ApiVersion = EOS_PLATFORM_OPTIONS_API_LATEST;
	Options.ProductId = ProductUtf8.Get();
	Options.SandboxId = SandboxUtf8.Get();
	Options.DeploymentId = DeploymentUtf8.Get();
	Options.ClientCredentials.ClientId = ClientUtf8.Get();
	Options.ClientCredentials.ClientSecret = SecretUtf8.Get();
	Options.bIsServer = EOS_FALSE;
	Options.EncryptionKey = KeyUtf8.Get();
	Options.CacheDirectory = CacheUtf8.Get();
	Options.Flags = EOS_PF_DISABLE_OVERLAY;
	Platform = Manager->CreatePlatform(Options);
	if (!Platform.IsValid())
	{
		UE_LOG(LogGWOnline, Warning, TEXT("GWEOS: could not create the platform"));
		return false;
	}
	return true;
}

void UGWOnlineSubsystem::HostGame(const FString& Options)
{
	Error.Reset();
	PendingOptions = Options;
	Op = EOp::Host;
	Deadline = FPlatformTime::Seconds() + HostTimeout;
	DestroySession();
	Login();
}

void UGWOnlineSubsystem::JoinByCode(const FString& InCode, const FString& PlayerName)
{
	Error.Reset();
	Code = InCode.TrimStartAndEnd().ToUpper();
	PendingName = PlayerName;
	Op = EOp::Join;
	Deadline = FPlatformTime::Seconds() + JoinTimeout;
	NextSearch = 0;
	Login();
}

void UGWOnlineSubsystem::Cancel()
{
	Op = EOp::None;
	NextSearch = 0;
	DestroySession();
}

FString UGWOnlineSubsystem::ConsumeError()
{
	FString Out = Error;
	Error.Reset();
	return Out;
}

void UGWOnlineSubsystem::Login()
{
	if (!EnsurePlatform())
	{
		if (Op == EOp::Host) { HostOverIp(TEXT("configuration EOS")); } else { Fail(TEXT("Service en ligne indisponible.")); }
		return;
	}
	if (LocalUser)
	{
		AfterLogin();
		return;
	}
	if (bLoggingIn)
	{
		return;
	}
	bLoggingIn = true;
	if (bFreshDevice)
	{
		// test only: a second instance on this PC needs its own identity
		bFreshDevice = false;
		EOS_Connect_DeleteDeviceIdOptions Options = {};
		Options.ApiVersion = EOS_CONNECT_DELETEDEVICEID_API_LATEST;
		EOS_Connect_DeleteDeviceId(EOS_Platform_GetConnectInterface(*Platform), &Options, this,
			[](const EOS_Connect_DeleteDeviceIdCallbackInfo* Data) { static_cast<UGWOnlineSubsystem*>(Data->ClientData)->OnDeviceIdDeleted(); });
		return;
	}
	OnDeviceIdDeleted();
}

void UGWOnlineSubsystem::OnDeviceIdDeleted()
{
	EOS_Connect_CreateDeviceIdOptions Options = {};
	Options.ApiVersion = EOS_CONNECT_CREATEDEVICEID_API_LATEST;
	Options.DeviceModel = "PC Windows";
	EOS_Connect_CreateDeviceId(EOS_Platform_GetConnectInterface(*Platform), &Options, this,
		[](const EOS_Connect_CreateDeviceIdCallbackInfo* Data) { static_cast<UGWOnlineSubsystem*>(Data->ClientData)->OnDeviceIdCreated((int32)Data->ResultCode); });
}

void UGWOnlineSubsystem::OnDeviceIdCreated(int32 Result)
{
	const EOS_EResult Outcome = (EOS_EResult)Result;
	if (Outcome != EOS_EResult::EOS_Success && Outcome != EOS_EResult::EOS_DuplicateNotAllowed)
	{
		bLoggingIn = false;
		UE_LOG(LogGWOnline, Warning, TEXT("GWEOS: device id failed: %s"), *ResultText(Outcome));
		if (Op == EOp::Host) { HostOverIp(ResultText(Outcome)); } else if (Op == EOp::Join) { Fail(TEXT("Connexion aux services en ligne impossible.")); }
		return;
	}
	LoginWithDeviceId();
}

void UGWOnlineSubsystem::LoginWithDeviceId()
{
	EOS_Connect_Credentials Credentials = {};
	Credentials.ApiVersion = EOS_CONNECT_CREDENTIALS_API_LATEST;
	Credentials.Token = nullptr;
	Credentials.Type = EOS_EExternalCredentialType::EOS_ECT_DEVICEID_ACCESS_TOKEN;

	EOS_Connect_UserLoginInfo Info = {};
	Info.ApiVersion = EOS_CONNECT_USERLOGININFO_API_LATEST;
	Info.DisplayName = "Convive";

	EOS_Connect_LoginOptions Options = {};
	Options.ApiVersion = EOS_CONNECT_LOGIN_API_LATEST;
	Options.Credentials = &Credentials;
	Options.UserLoginInfo = &Info;
	EOS_Connect_Login(EOS_Platform_GetConnectInterface(*Platform), &Options, this,
		[](const EOS_Connect_LoginCallbackInfo* Data) { static_cast<UGWOnlineSubsystem*>(Data->ClientData)->OnLogin((int32)Data->ResultCode, Data->LocalUserId, Data->ContinuanceToken); });
}

void UGWOnlineSubsystem::OnLogin(int32 Result, void* UserId, void* ContinuanceToken)
{
	const EOS_EResult Outcome = (EOS_EResult)Result;
	if (Outcome == EOS_EResult::EOS_InvalidUser && ContinuanceToken)
	{
		// first time on this device: make its Epic product user
		EOS_Connect_CreateUserOptions Options = {};
		Options.ApiVersion = EOS_CONNECT_CREATEUSER_API_LATEST;
		Options.ContinuanceToken = (EOS_ContinuanceToken)ContinuanceToken;
		EOS_Connect_CreateUser(EOS_Platform_GetConnectInterface(*Platform), &Options, this,
			[](const EOS_Connect_CreateUserCallbackInfo* Data) { static_cast<UGWOnlineSubsystem*>(Data->ClientData)->OnLogin((int32)Data->ResultCode, Data->LocalUserId, nullptr); });
		return;
	}
	bLoggingIn = false;
	if (Outcome != EOS_EResult::EOS_Success || !UserId)
	{
		UE_LOG(LogGWOnline, Warning, TEXT("GWEOS: login failed: %s"), *ResultText(Outcome));
		if (Op == EOp::Host) { HostOverIp(ResultText(Outcome)); } else if (Op == EOp::Join) { Fail(TEXT("Connexion aux services en ligne impossible.")); }
		return;
	}
	LocalUser = UserId;
	UE_LOG(LogGWOnline, Log, TEXT("GWEOS: logged in"));

	if (AuthNotify == 0)
	{
		// the token lasts about an hour: renew it during long evenings
		EOS_Connect_AddNotifyAuthExpirationOptions Options = {};
		Options.ApiVersion = EOS_CONNECT_ADDNOTIFYAUTHEXPIRATION_API_LATEST;
		AuthNotify = EOS_Connect_AddNotifyAuthExpiration(EOS_Platform_GetConnectInterface(*Platform), &Options, this,
			[](const EOS_Connect_AuthExpirationCallbackInfo* Data) { static_cast<UGWOnlineSubsystem*>(Data->ClientData)->OnDeviceIdCreated((int32)EOS_EResult::EOS_Success); });
	}
	if (!Sockets.IsValid())
	{
		Sockets = MakeShareable(new FSocketSubsystemEOS(Platform, MakeShared<FGWSocketUtils>(this)));
		FString SocketError;
		if (!Sockets->Init(SocketError))
		{
			UE_LOG(LogGWOnline, Warning, TEXT("GWEOS: socket subsystem init failed: %s"), *SocketError);
		}
	}
	AfterLogin();
}

void UGWOnlineSubsystem::AfterLogin()
{
	if (Op == EOp::Host)
	{
		CreateSession();
	}
	else if (Op == EOp::Join)
	{
		Search();
	}
}

void UGWOnlineSubsystem::CreateSession()
{
	Code = NewCode();
	SessionName = FString(TEXT("GW_")) + Code;
	const FTCHARToUTF8 NameUtf8(*SessionName), CodeUtf8(*Code);

	char PuidBuffer[EOS_PRODUCTUSERID_MAX_LENGTH + 1];
	int32 PuidLen = sizeof(PuidBuffer);
	EOS_ProductUserId_ToString((EOS_ProductUserId)LocalUser, PuidBuffer, &PuidLen);
	const FString HostAddress = FString::Printf(TEXT("EOS:%s"), UTF8_TO_TCHAR(PuidBuffer));
	const FTCHARToUTF8 AddressUtf8(*HostAddress);

	EOS_HSessions Sessions = EOS_Platform_GetSessionsInterface(*Platform);
	EOS_Sessions_CreateSessionModificationOptions CreateOptions = {};
	CreateOptions.ApiVersion = EOS_SESSIONS_CREATESESSIONMODIFICATION_API_LATEST;
	CreateOptions.SessionName = NameUtf8.Get();
	CreateOptions.BucketId = Bucket;
	CreateOptions.MaxPlayers = MaxPlayers;
	CreateOptions.LocalUserId = (EOS_ProductUserId)LocalUser;
	CreateOptions.bPresenceEnabled = EOS_FALSE;
	EOS_HSessionModification Mod = nullptr;
	EOS_EResult Result = EOS_Sessions_CreateSessionModification(Sessions, &CreateOptions, &Mod);

	if (Result == EOS_EResult::EOS_Success)
	{
		EOS_SessionModification_SetPermissionLevelOptions Permission = {};
		Permission.ApiVersion = EOS_SESSIONMODIFICATION_SETPERMISSIONLEVEL_API_LATEST;
		Permission.PermissionLevel = EOS_EOnlineSessionPermissionLevel::EOS_OSPF_PublicAdvertised;
		EOS_SessionModification_SetPermissionLevel(Mod, &Permission);

		EOS_SessionModification_SetJoinInProgressAllowedOptions InProgress = {};
		InProgress.ApiVersion = EOS_SESSIONMODIFICATION_SETJOININPROGRESSALLOWED_API_LATEST;
		InProgress.bAllowJoinInProgress = EOS_TRUE;
		EOS_SessionModification_SetJoinInProgressAllowed(Mod, &InProgress);

		EOS_SessionModification_SetHostAddressOptions Host = {};
		Host.ApiVersion = EOS_SESSIONMODIFICATION_SETHOSTADDRESS_API_LATEST;
		Host.HostAddress = AddressUtf8.Get();
		EOS_SessionModification_SetHostAddress(Mod, &Host);

		EOS_Sessions_AttributeData Attribute = {};
		Attribute.ApiVersion = EOS_SESSIONS_SESSIONATTRIBUTEDATA_API_LATEST;
		Attribute.Key = AttrCode;
		Attribute.Value.AsUtf8 = CodeUtf8.Get();
		Attribute.ValueType = EOS_EAttributeType::EOS_AT_STRING;
		EOS_SessionModification_AddAttributeOptions Add = {};
		Add.ApiVersion = EOS_SESSIONMODIFICATION_ADDATTRIBUTE_API_LATEST;
		Add.SessionAttribute = &Attribute;
		Add.AdvertisementType = EOS_ESessionAttributeAdvertisementType::EOS_SAAT_Advertise;
		Result = EOS_SessionModification_AddAttribute(Mod, &Add);
	}
	if (Result != EOS_EResult::EOS_Success)
	{
		if (Mod) { EOS_SessionModification_Release(Mod); }
		SessionName.Reset();
		HostOverIp(ResultText(Result));
		return;
	}

	EOS_Sessions_UpdateSessionOptions Update = {};
	Update.ApiVersion = EOS_SESSIONS_UPDATESESSION_API_LATEST;
	Update.SessionModificationHandle = Mod;
	EOS_Sessions_UpdateSession(Sessions, &Update, this,
		[](const EOS_Sessions_UpdateSessionCallbackInfo* Data) { static_cast<UGWOnlineSubsystem*>(Data->ClientData)->OnSessionUpdated((int32)Data->ResultCode); });
	EOS_SessionModification_Release(Mod);
}

void UGWOnlineSubsystem::OnSessionUpdated(int32 Result)
{
	const EOS_EResult Outcome = (EOS_EResult)Result;
	if (Op != EOp::Host)
	{
		DestroySession();
		return;
	}
	if (Outcome != EOS_EResult::EOS_Success)
	{
		SessionName.Reset();
		HostOverIp(ResultText(Outcome));
		return;
	}
	Op = EOp::None;
	UE_LOG(LogGWOnline, Log, TEXT("GWEOS: code=%s"), *Code);
	FPlatformApplicationMisc::ClipboardCopy(*Code);
	OverlayText = FString::Printf(TEXT("CODE DE PARTIE   %s   (copié)"), *Code);
	OverlayUntil = FPlatformTime::Seconds() + CodeOnScreen;
	OpenManor(PendingOptions);
}

void UGWOnlineSubsystem::DestroySession()
{
	if (Platform.IsValid() && !SessionName.IsEmpty())
	{
		const FTCHARToUTF8 NameUtf8(*SessionName);
		EOS_Sessions_DestroySessionOptions Options = {};
		Options.ApiVersion = EOS_SESSIONS_DESTROYSESSION_API_LATEST;
		Options.SessionName = NameUtf8.Get();
		EOS_Sessions_DestroySession(EOS_Platform_GetSessionsInterface(*Platform), &Options, nullptr,
			[](const EOS_Sessions_DestroySessionCallbackInfo*) {});
	}
	SessionName.Reset();
	OverlayText.Reset();
}

void UGWOnlineSubsystem::Search()
{
	if (SearchHandle)
	{
		return;
	}
	EOS_HSessions Sessions = EOS_Platform_GetSessionsInterface(*Platform);
	EOS_Sessions_CreateSessionSearchOptions CreateOptions = {};
	CreateOptions.ApiVersion = EOS_SESSIONS_CREATESESSIONSEARCH_API_LATEST;
	CreateOptions.MaxSearchResults = 1;
	EOS_HSessionSearch Handle = nullptr;
	EOS_EResult Result = EOS_Sessions_CreateSessionSearch(Sessions, &CreateOptions, &Handle);
	if (Result == EOS_EResult::EOS_Success)
	{
		const FTCHARToUTF8 CodeUtf8(*Code);
		EOS_Sessions_AttributeData Attribute = {};
		Attribute.ApiVersion = EOS_SESSIONS_SESSIONATTRIBUTEDATA_API_LATEST;
		Attribute.Key = AttrCode;
		Attribute.Value.AsUtf8 = CodeUtf8.Get();
		Attribute.ValueType = EOS_EAttributeType::EOS_AT_STRING;
		EOS_SessionSearch_SetParameterOptions Parameter = {};
		Parameter.ApiVersion = EOS_SESSIONSEARCH_SETPARAMETER_API_LATEST;
		Parameter.Parameter = &Attribute;
		Parameter.ComparisonOp = EOS_EComparisonOp::EOS_CO_EQUAL;
		Result = EOS_SessionSearch_SetParameter(Handle, &Parameter);
	}
	if (Result != EOS_EResult::EOS_Success)
	{
		if (Handle) { EOS_SessionSearch_Release(Handle); }
		Fail(TEXT("Recherche de la partie impossible."));
		return;
	}
	SearchHandle = Handle;
	EOS_SessionSearch_FindOptions Find = {};
	Find.ApiVersion = EOS_SESSIONSEARCH_FIND_API_LATEST;
	Find.LocalUserId = (EOS_ProductUserId)LocalUser;
	EOS_SessionSearch_Find(Handle, &Find, this,
		[](const EOS_SessionSearch_FindCallbackInfo* Data) { static_cast<UGWOnlineSubsystem*>(Data->ClientData)->OnSearchDone((int32)Data->ResultCode); });
}

void UGWOnlineSubsystem::OnSearchDone(int32 Result)
{
	EOS_HSessionSearch Handle = (EOS_HSessionSearch)SearchHandle;
	SearchHandle = nullptr;
	FString HostAddress;
	if ((EOS_EResult)Result == EOS_EResult::EOS_Success && Op == EOp::Join)
	{
		EOS_SessionSearch_GetSearchResultCountOptions CountOptions = {};
		CountOptions.ApiVersion = EOS_SESSIONSEARCH_GETSEARCHRESULTCOUNT_API_LATEST;
		if (EOS_SessionSearch_GetSearchResultCount(Handle, &CountOptions) > 0)
		{
			EOS_SessionSearch_CopySearchResultByIndexOptions CopyOptions = {};
			CopyOptions.ApiVersion = EOS_SESSIONSEARCH_COPYSEARCHRESULTBYINDEX_API_LATEST;
			CopyOptions.SessionIndex = 0;
			EOS_HSessionDetails Details = nullptr;
			if (EOS_SessionSearch_CopySearchResultByIndex(Handle, &CopyOptions, &Details) == EOS_EResult::EOS_Success)
			{
				EOS_SessionDetails_CopyInfoOptions InfoOptions = {};
				InfoOptions.ApiVersion = EOS_SESSIONDETAILS_COPYINFO_API_LATEST;
				EOS_SessionDetails_Info* Info = nullptr;
				if (EOS_SessionDetails_CopyInfo(Details, &InfoOptions, &Info) == EOS_EResult::EOS_Success)
				{
					HostAddress = UTF8_TO_TCHAR(Info->HostAddress);
					EOS_SessionDetails_Info_Release(Info);
				}
				EOS_SessionDetails_Release(Details);
			}
		}
	}
	EOS_SessionSearch_Release(Handle);

	if (Op != EOp::Join)
	{
		return;
	}
	if (HostAddress.IsEmpty())
	{
		// a new game takes a few seconds to be advertised: Tick searches again until the deadline
		NextSearch = FPlatformTime::Seconds() + SearchEvery;
		return;
	}
	Op = EOp::None;
	NextSearch = 0;
	UE_LOG(LogGWOnline, Log, TEXT("GWEOS: found the game, joining"));
	UGameInstance* GI = GetGameInstance();
	APlayerController* PC = GI ? GI->GetFirstLocalPlayerController() : nullptr;
	if (!PC)
	{
		Fail(TEXT("Impossible de rejoindre la partie."));
		return;
	}
	// brackets: FURL would otherwise read "EOS:" as a protocol and the id as a map (same form as Epic's OnlineSessionEOS)
	PC->ClientTravel(FString::Printf(TEXT("[%s]?Name=%s"), *HostAddress, *PendingName), TRAVEL_Absolute);
}

void UGWOnlineSubsystem::HostOverIp(const FString& Why)
{
	UE_LOG(LogGWOnline, Warning, TEXT("GWEOS: no code game (%s): hosting over IP"), *Why);
	Op = EOp::None;
	OverlayText = TEXT("PAS DE CODE : SERVICE EN LIGNE INJOIGNABLE. PARTIE PAR ADRESSE IP");
	OverlayUntil = FPlatformTime::Seconds() + 30.0;
	OpenManor(PendingOptions + TEXT("?bUseIPSockets"));
}

void UGWOnlineSubsystem::Fail(const FString& Message)
{
	UE_LOG(LogGWOnline, Warning, TEXT("GWEOS: %s"), *Message);
	Op = EOp::None;
	NextSearch = 0;
	Error = Message;
}

void UGWOnlineSubsystem::OpenManor(const FString& Options)
{
	if (UGameInstance* GI = GetGameInstance())
	{
		UGameplayStatics::OpenLevel(GI, ManorMap, true, Options);
	}
}

bool UGWOnlineSubsystem::Tick(float Dt)
{
	const double Now = FPlatformTime::Seconds();
	if (AutoAt > 0 && Now >= AutoAt)
	{
		AutoAt = 0;
		if (bAutoHost)
		{
			HostGame(TEXT("listen?Name=Hote"));
		}
		else
		{
			JoinByCode(AutoJoin, TEXT("Invite"));
		}
	}
	if (Op != EOp::None && Now >= Deadline)
	{
		if (Op == EOp::Host) { HostOverIp(TEXT("délai dépassé")); } else { Fail(FString::Printf(TEXT("Aucune partie trouvée avec le code %s."), *Code)); }
	}
	if (Op == EOp::Join && NextSearch > 0 && Now >= NextSearch)
	{
		NextSearch = 0;
		Search();
	}
	return true;
}

void UGWOnlineSubsystem::OnMapLoaded(UWorld* World)
{
	RefreshOverlay(World);
}

void UGWOnlineSubsystem::RefreshOverlay(UWorld* World)
{
	if (!World || World->GetGameInstance() != GetGameInstance() || !World->GetGameViewport() || OverlayText.IsEmpty())
	{
		return;
	}
	UGameViewportClient* Viewport = World->GetGameViewport();
	if (Overlay.IsValid() && OverlayViewport.Get() == Viewport)
	{
		Viewport->RemoveViewportWidgetContent(Overlay.ToSharedRef());
	}
	TWeakObjectPtr<UGWOnlineSubsystem> Weak(this);
	// bottom right, above the money: the host reads it to the others, Tab brings it back after three minutes
	Overlay = SNew(SBox)
		.HAlign(HAlign_Right)
		.VAlign(VAlign_Bottom)
		.Padding(FMargin(0, 0, 40, 130))
		.Visibility_Lambda([Weak]()
		{
			const UGWOnlineSubsystem* Self = Weak.Get();
			if (!Self || Self->OverlayText.IsEmpty()) { return EVisibility::Collapsed; }
			const UGameInstance* GI = Self->GetGameInstance();
			const APlayerController* PC = GI ? GI->GetFirstLocalPlayerController() : nullptr;
			const bool bTab = PC && PC->IsInputKeyDown(EKeys::Tab);
			return (bTab || FPlatformTime::Seconds() < Self->OverlayUntil) ? EVisibility::HitTestInvisible : EVisibility::Collapsed;
		})
		[
			SNew(SBorder)
			.BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
			.BorderBackgroundColor(FLinearColor(0.02f, 0.015f, 0.01f, 0.75f))
			.Padding(FMargin(16, 8))
			[
				SNew(STextBlock)
				.Text_Lambda([Weak]() { return Weak.IsValid() ? FText::FromString(Weak->OverlayText) : FText::GetEmpty(); })
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 22))
				.ColorAndOpacity(FLinearColor(0.95f, 0.76f, 0.36f))
			]
		];
	OverlayViewport = Viewport;
	Viewport->AddViewportWidgetContent(Overlay.ToSharedRef(), 50);
}

static UGWOnlineSubsystem* GetOnline(UObject* Context)
{
	UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(Context, EGetWorldErrorMode::LogAndReturnNull) : nullptr;
	UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
	return GI ? GI->GetSubsystem<UGWOnlineSubsystem>() : nullptr;
}

void UGWOnlineLibrary::GWHostGame(UObject* Context, const FString& Options)
{
	if (UGWOnlineSubsystem* Online = GetOnline(Context)) { Online->HostGame(Options); }
}

void UGWOnlineLibrary::GWJoinByCode(UObject* Context, const FString& Code, const FString& PlayerName)
{
	if (UGWOnlineSubsystem* Online = GetOnline(Context)) { Online->JoinByCode(Code, PlayerName); }
}

void UGWOnlineLibrary::GWCancelOnline(UObject* Context)
{
	if (UGWOnlineSubsystem* Online = GetOnline(Context)) { Online->Cancel(); }
}

FString UGWOnlineLibrary::GWConsumeError(UObject* Context)
{
	UGWOnlineSubsystem* Online = GetOnline(Context);
	return Online ? Online->ConsumeError() : FString();
}

bool UGWOnlineLibrary::GWIsGameCode(const FString& Text)
{
	const FString Clean = Text.TrimStartAndEnd();
	if (Clean.Len() != 6)
	{
		return false;
	}
	for (const TCHAR Char : Clean)
	{
		if (!FChar::IsAlnum(Char))
		{
			return false;
		}
	}
	return true;
}

// Join-by-code online play through Epic Online Services: device login (no Epic account), an advertised session
// holding the code, and P2P with Epic's relays through the engine's NetDriverEOS. IP play is unchanged: the EOS socket
// subsystem only exists once a code game was asked for, and NetDriverEOS passes through to IP until then.
#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "IEOSSDKManager.h"
#include "GWOnline.generated.h"

class FSocketSubsystemEOS;
class SWidget;
class UGameViewportClient;

UCLASS()
class UGWOnlineSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()
public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	void HostGame(const FString& Options);
	void JoinByCode(const FString& Code, const FString& PlayerName);
	void Cancel();
	FString ConsumeError();

	// internal: EOS callbacks
	void OnDeviceIdDeleted();
	void OnDeviceIdCreated(int32 Result);
	void OnLogin(int32 Result, void* UserId, void* ContinuanceToken);
	void OnSessionUpdated(int32 Result);
	void OnSearchDone(int32 Result);
	void* GetLocalUser() const { return LocalUser; }
	const FString& GetSessionName() const { return SessionName; }

private:
	enum class EOp : uint8 { None, Host, Join };

	bool Tick(float Dt);
	bool EnsurePlatform();
	void Login();
	void LoginWithDeviceId();
	void AfterLogin();
	void CreateSession();
	void DestroySession();
	void Search();
	void HostOverIp(const FString& Why);
	void Fail(const FString& Message);
	void OpenManor(const FString& Options);
	void RefreshOverlay(UWorld* World);
	void OnMapLoaded(UWorld* World);

	IEOSPlatformHandlePtr Platform;
	TSharedPtr<FSocketSubsystemEOS> Sockets;
	void* LocalUser = nullptr;
	bool bLoggingIn = false;
	bool bFreshDevice = false;
	uint64 AuthNotify = 0;

	EOp Op = EOp::None;
	double Deadline = 0;
	double NextSearch = 0;
	FString PendingOptions;
	FString PendingName;
	FString Code;
	FString SessionName;
	FString Error;
	void* SearchHandle = nullptr;

	FString OverlayText;
	double OverlayUntil = 0;
	TSharedPtr<SWidget> Overlay;
	TWeakObjectPtr<UGameViewportClient> OverlayViewport;

	FTSTicker::FDelegateHandle TickHandle;
	FDelegateHandle MapHandle;
	double AutoAt = 0;
	FString AutoJoin;
	bool bAutoHost = false;
};

UCLASS()
class UGWOnlineLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/** Log in to Epic, publish a code, open the manor. Falls back to plain IP hosting when Epic can't be reached. Options as for OpenLevel. */
	UFUNCTION(BlueprintCallable, Category = "GWOnline", meta = (WorldContext = "WorldContextObject"))
	static void GWHostGame(UObject* WorldContextObject, const FString& Options);

	UFUNCTION(BlueprintCallable, Category = "GWOnline", meta = (WorldContext = "WorldContextObject"))
	static void GWJoinByCode(UObject* WorldContextObject, const FString& Code, const FString& PlayerName);

	UFUNCTION(BlueprintCallable, Category = "GWOnline", meta = (WorldContext = "WorldContextObject"))
	static void GWCancelOnline(UObject* WorldContextObject);

	/** The message of the last failed code join, once; empty otherwise. */
	UFUNCTION(BlueprintCallable, Category = "GWOnline", meta = (WorldContext = "WorldContextObject"))
	static FString GWConsumeError(UObject* WorldContextObject);

	/** True for 6 letters or digits (a game code), false for an IP address or a host name. */
	UFUNCTION(BlueprintPure, Category = "GWOnline")
	static bool GWIsGameCode(const FString& Text);
};

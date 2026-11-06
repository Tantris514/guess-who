using UnrealBuildTool;
public class GuessWho : ModuleRules
{
	public GuessWho(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "EOSShared" });
		PrivateDependencyModuleNames.AddRange(new string[] { "InputCore", "Slate", "SlateCore", "ApplicationCore", "Sockets", "EOSSDK", "SocketSubsystemEOS" });
	}
}

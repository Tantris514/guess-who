using UnrealBuildTool;
public class GuessWhoTarget : TargetRules
{
	public GuessWhoTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("GuessWho");
	}
}

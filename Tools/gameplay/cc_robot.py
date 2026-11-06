"""Rebuild only BP_GW_RobotController from s32_events.py (its source of truth), without a full s32 run.

s32 is long and rewrites the character, game state, game mode and controller graphs; for a robot-only change this runs
s32's preamble constants, its controller() / THINK / ROAM / EG / gm_call helpers and its robot section, nothing else.
Usage: ue_run.py cc_robot.py   (camera & combat agent, authorized by the coordinator for the robot parts of s32)"""
import unreal

P = r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\s32_events.py'
L = open(P, encoding='utf-8').read().split('\n')


def find(prefix, start=0):
    return next(i for i in range(start, len(L)) if L[i].startswith(prefix))


pre = L[find('import sys'):find('def mi(')]
helpers = L[find('def controller('):find('bandit = controller(')]
robot = L[find('robot = controller('):find('save(robot)') + 1]
src = '\n'.join(pre + ["ch = load_bp('BP_GW_Character')", 'chc = ch.generated_class()'] + helpers + robot)
g = {'__name__': '__main__', 'unreal': unreal, 'UE_ARGS': [], '__file__': P}
exec(compile(src, P + ' (robot section)', 'exec'), g)

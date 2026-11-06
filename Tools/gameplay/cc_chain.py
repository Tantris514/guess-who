"""Camera & combat agent: run several editor scripts in one remote call (one lock window instead of five).
UE_ARGS: a list of "script.py[:Arg1,Arg2]" items, run in order; a failure is reported and the chain goes on."""
import unreal, os, traceback

D = r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay'
for item in UE_ARGS:
    name, _, args = item.rpartition(':') if item.count(':') > (1 if item[1:2] == ':' else 0) else (item, '', '')
    path = os.path.join(D, name)
    print(f'===== {name} {args}')
    g = {'__name__': '__main__', 'unreal': unreal, 'UE_ARGS': [a for a in args.split(',') if a], '__file__': path}
    try:
        exec(compile(open(path, encoding='utf-8').read(), path, 'exec'), g)
    except SystemExit:
        pass
    except Exception:
        print('CHAIN FAILED', name, traceback.format_exc()[-1500:])

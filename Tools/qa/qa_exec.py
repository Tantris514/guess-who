"""Run Python inside the shared editor (remote exec on 239.0.0.1:6766; GW_RX_PORT overrides).

  python -I -X utf8 qa_exec.py script.py      |      python -I -X utf8 qa_exec.py -c "print(1)"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shoot_cams import Editor  # noqa: E402


def main():
    code = sys.argv[2] if sys.argv[1] == "-c" else open(sys.argv[1], encoding="utf-8").read()
    ed = Editor(int(os.environ.get("GW_RX_PORT", "6766")))
    try:
        print(ed.run("import unreal\n" + code))
    finally:
        ed.close()


if __name__ == "__main__":
    main()

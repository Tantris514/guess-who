"""Tiny exclusive lock for logs/sched_plan.json (written by vox_sched.py and vox_worker.py)."""
import os, time
from contextlib import contextmanager


@contextmanager
def plan_lock(path, timeout=30):
    lock = path + ".lock"
    t0 = time.time()
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd); break
        except FileExistsError:
            if time.time() - t0 > timeout:
                try:
                    os.remove(lock)   # stale lock (a crashed writer)
                except OSError:
                    pass
            time.sleep(0.2)
    try:
        yield
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass

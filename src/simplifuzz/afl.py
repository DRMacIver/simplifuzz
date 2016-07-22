from collections import namedtuple
import os
import sysv_ipc
import subprocess
import signal


SHM_ENV_VAR = "__AFL_SHM_ID"
AFL_MAP_SIZE = 1 << 16

BUCKET_LOOKUP = []

for u, v, c in [
    (0, 0, 0), (1, 1, 1), (2, 2, 2), (3, 3, 3),
    (4, 7, 4), (8, 15, 5), (16, 31, 6), (32, 127, 7), (128, 255, 8)
]:
    for i in range(u, v + 1):
        assert len(BUCKET_LOOKUP) == i
        BUCKET_LOOKUP.append(c)
assert len(BUCKET_LOOKUP) == 256


AFLResponse = namedtuple('AFLResponse', ('status', 'labels', 'timeout'))

def signal_group(sp, signal):
    gid = os.getpgid(sp.pid)
    assert gid != os.getgid()
    os.killpg(gid, signal)


def interrupt_wait_and_kill(sp):
    if sp.returncode is None:
        # In case the subprocess forked. Python might hang if you don't close
        # all pipes.
        for pipe in [sp.stdout, sp.stderr, sp.stdin]:
            if pipe:
                pipe.close()
        signal_group(sp, signal.SIGINT)
        for _ in range(10):
            if sp.poll() is not None:
                return
            time.sleep(0.1)
        signal_group(sp, signal.SIGKILL)

SHARED = sysv_ipc.SharedMemory(
    key=sysv_ipc.IPC_PRIVATE,
    flags=sysv_ipc.IPC_CREAT,
    size=AFL_MAP_SIZE, init_character=b'\0')

os.environ[SHM_ENV_VAR] = str(SHARED.id)

ZERO = b'\0' * AFL_MAP_SIZE

def run_program(command, data, timeout=1):
    env = os.environ.copy()

    SHARED.write(ZERO)

    sp = subprocess.Popen(
        command, stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        universal_newlines=False,
        preexec_fn=os.setsid, shell=True, env=env
    )
    timed_out = False
    try:
        try:
            sp.stdin.write(data)
            sp.stdin.close()
        except BrokenPipeError:
            pass
        sp.wait(timeout=timeout)
        returncode = sp.returncode
    except subprocess.TimeoutExpired as e:
        timed_out = True
        returncode = -1
    except subprocess.CalledProcessError as e:
        returncode = e.returncode
    finally:
        interrupt_wait_and_kill(sp)

    labels = []
    for i, c in enumerate(SHARED.read()):
        if c > 0:
            labels.append((i, BUCKET_LOOKUP[c]))
    return AFLResponse(returncode, labels, timed_out)

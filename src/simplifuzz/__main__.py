from simplifuzz.fuzzer import Fuzzer, LifeCycle
import hashlib
import os
import sys
import subprocess
import click
import signal
import time


TIMEOUT = 10


class MainLifecycle(LifeCycle):
    def __init__(self, corpus, debug):
        self.__corpus = corpus
        self.__debug = debug

    def debug(self, msg):
        if self.__debug:
            print(msg)

    def shrink_start(self, shrinker):
        self.debug("Starting pass %s" % (shrinker.__name__,))

    def shrink_finish(self, shrinker, count):
        self.debug(
            "Pass %s performed %d shrinks" % (shrinker.__name__, count))

    def __path(self, string):
        return os.path.relpath(os.path.join(
            self.__corpus, hashlib.sha1(string).hexdigest()[:8]))

    def item_added(self, string):
        p = self.__path(string)
        with open(p, 'wb') as o:
            o.write(string)
        if self.__debug:
            print("Created corpus item %r" % (p,))

    def item_removed(self, string):
        p = self.__path(string)
        os.unlink(p)
        if self.__debug:
            print("Removed corpus item %r" % (p,))

    def labels_improved(self, labels):
        if self.__debug:
            print("Improved %d labels" % (len(labels),))

    def new_labels(self, labels):
        if self.__debug:
            print("Discovered %d new labels" % (len(labels),))

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


@click.command()
@click.argument('test')
@click.argument('source', type=click.Path(file_okay=True, resolve_path=True))
@click.option(
    '--timeout', default=1, type=click.FLOAT, help=(
        'Time out subprocesses after this many seconds. If set to <= 0 then '
        'no timeout will be used.'))
@click.option(
    '--working', default='working',
    type=click.Path(file_okay=False, resolve_path=True))
@click.option('--debug', default=False, is_flag=True, help=(
    'Emit (extremely verbose) debug output while shrinking'
))
def simplifuzz(test, source, working, timeout, debug):
    def classify(string):
        sp = subprocess.Popen(
            test, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            universal_newlines=False,
            preexec_fn=os.setsid, shell=True,
        )
        try:
            result, _ = sp.communicate(string, timeout=timeout)
        except subprocess.TimeoutExpired:
            path = os.path.join(
                timeouts, hashlib.sha1(string).hexdigest()[:8])
            with open(path, 'wb') as o:
                o.write(string)
            return ()
        except subprocess.CalledProcessError as e:
            path = os.path.join(
                crashes, hashlib.sha1(string).hexdigest()[:8])                
            with open(path, 'wb') as o:
                o.write(string)
            return ()
        finally:
            interrupt_wait_and_kill(sp)
        return set(s.strip() for s in result.split(b'\n'))

    corpus = os.path.join(working, "corpus")
    crashes = os.path.join(working, "crashes")
    timeouts = os.path.join(working, "timeouts")

    for f in [working, corpus, crashes, timeouts]:
        try:
            os.mkdir(f)
        except OSError:
            pass

    fuzzer = Fuzzer(classify, MainLifecycle(corpus, debug))
    for f in os.listdir(corpus):
        path = os.path.join(corpus, f)
        if not os.path.isfile(path):
            continue
        tmp = path + ".garbage"
        os.rename(path, tmp)
        try:
            with open(tmp, 'rb') as i:
                fuzzer.incorporate(i.read())
        finally:
            os.unlink(tmp)

    if os.path.isfile(source):
        with open(source, 'rb') as i:
            fuzzer.incorporate(i.read())
    else:
        for f in os.listdir(source):
            path = os.path.join(source, f)
            if not os.path.isfile(path):
                continue
            with open(path, 'rb') as i:
                fuzzer.incorporate(i.read())
    fuzzer.fuzz()


if __name__ == '__main__':
    simplifuzz()

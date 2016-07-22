from simplifuzz.fuzzer import Fuzzer, LifeCycle
import hashlib
import os
import sys
import subprocess
import click
import signal
import time
from simplifuzz.afl import run_program


TIMEOUT = 10


class MainLifecycle(LifeCycle):
    def __init__(self, corpus, label_file, debug):
        self.__corpus = corpus
        self.__debug = debug
        self.__label_file = label_file


    def debug(self, msg):
        if self.__debug:
            print(msg)

    def shrink_start(self, shrinker):
        self.debug("Starting pass %s" % (shrinker.__name__,))

    def shrink_finish(self, shrinker, count):
        self.debug(
            "Pass %s made %d changes " % (shrinker.__name__, count))

    def __path(self, string):
        return os.path.relpath(os.path.join(
            self.__corpus, "%d-%s" % (len(string),
                hashlib.sha1(string).hexdigest()[:8])))

    def item_added(self, string):
        p = self.__path(string)
        with open(p, 'wb') as o:
            o.write(string)
        self.debug("Created corpus item %r" % (p,))

    def item_removed(self, string):
        p = self.__path(string)
        os.unlink(p)
        self.debug("Removed corpus item %r" % (p,))

    def labels_improved(self, labels):
        self.debug("Improved %d labels" % (len(labels),))

    def new_labels(self, labels):
        self.debug("Discovered %d new labels" % (len(labels),))
        for l in labels:
            self.__label_file.write(b"%d:%d\n" % l)
            self.__label_file.flush()

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
@click.option(
    '--input', default='-', type=click.Path(resolve_path=True))
def simplifuzz(test, source, working, timeout, debug, input):
    def classify(string):
        if input == "-":
            result = run_program(test, string)
        else:
            with open(input, 'wb') as o:
                o.write(string)
            result = run_program(test, b'')
        if result.timeout:
            path = os.path.join(
                timeouts, hashlib.sha1(string).hexdigest()[:8])
            with open(path, 'wb') as o:
                o.write(string)
            return ()
        elif result.status < 0:
            path = os.path.join(
                crashes, hashlib.sha1(string).hexdigest()[:8])                
            with open(path, 'wb') as o:
                o.write(string)
            return ()
        else:
            return result.labels

    corpus = os.path.join(working, "corpus")
    crashes = os.path.join(working, "crashes")
    timeouts = os.path.join(working, "timeouts")

    for f in [working, corpus, crashes, timeouts]:
        try:
            os.mkdir(f)
        except OSError:
            pass

    label_file = open(os.path.join(working, "labels"), "wb")

    fuzzer = Fuzzer(classify, MainLifecycle(corpus, label_file, debug))

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

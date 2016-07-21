from sortedcontainers import SortedList
import hashlib
from collections import Counter


def cache_key(string):
    return hashlib.sha1(string).digest()[:8]


class LifeCycle(object):
    def shrink_start(self, shrinker):
        pass

    def shrink_finish(self, shrinker, count):
        pass

    def item_added(self, item):
        pass

    def item_removed(self, item):
        pass

    def new_labels(self, labels):
        pass

    def labels_improved(self, labels):
        pass


class Fuzzer(object):
    def __init__(self, classifier, lifecycle=None):
        self.__strings_by_tag = {}
        self.__corpus = SortedList()
        self.__refcounts = {}
        self.__classifier = classifier
        self.__seen = set()
        self.__lifecycle = lifecycle or LifeCycle()
        self.__counter = 0
        self.incorporate(b'')
        assert len(self.__corpus) == len(self.__refcounts) == len(self.__seen) \
            == 1

    def incorporate(self, string):
        key = cache_key(string)
        if key in self.__seen:
            return
        self.__seen.add(key)
        labels = self.__classifier(string)
        item = CorpusItem(string)
        new_labels = set()
        improved_labels = set()

        for l in labels:
            if (
                l not in self.__strings_by_tag or
                item < CorpusItem(self.__strings_by_tag[l])
            ):
                self.__incref(string)
                if l in self.__strings_by_tag:
                    self.__decref(self.__strings_by_tag[l])
                    improved_labels.add(l)
                else:
                    new_labels.add(l)
                self.__strings_by_tag[l] = string
        if new_labels:
            self.__lifecycle.new_labels(new_labels)
        if improved_labels:
            self.__lifecycle.labels_improved(improved_labels)

    def fuzz(self):
        prev = -1
        while self.__counter != prev:
            prev = self.__counter
            for shrinker in self.__shrinkers():
                self.__lifecycle.shrink_start(shrinker)
                initial_shrinks = self.__counter
                i = 0
                while i < len(self.__corpus):
                    target = self.__corpus[i].string
                    for s in shrinker(target):
                        self.incorporate(s)
                    i += 1
                self.__lifecycle.shrink_finish(
                    shrinker, self.__counter - initial_shrinks)

    def __shrinkers(self):
        n = len(self.__corpus[-1].string)
        while n > 1:
            yield self.__cutter(n, n)
            n //= 2

        yield self.__byte_clearing

        n = len(self.__corpus[-1].string)
        while n > 1:
            i = n
            while i > 0:
                yield self.__cutter(i, n)
                i //= 2
            n -= 1

    def __byte_clearing(self, string):
        counter = Counter(string)
        for c in sorted(counter, key=lambda x: (-counter[x], x)):
            yield string.replace(bytes([c]), b'')

    def __cutter(self, step, size):
        assert step > 0
        assert size > 0
        def accept(string):
            if size >= len(string):
                return
            i = 0
            while i + size <= len(string):
                yield string[:i] + string[i+size:]
                i += step
        accept.__name__ = '__cutter(%d, %d)' % (step, size)
        return accept


    def __incref(self, string):
        c = self.__refcounts.get(string, 0)
        assert c >= 0
        if c == 0:
            self.__counter += 1
            self.__corpus.add(CorpusItem(string))
            self.__lifecycle.item_added(string)
        self.__refcounts[string] = c + 1

    def __decref(self, string):
        assert self.__refcounts[string] > 0
        self.__refcounts[string] -= 1
        if self.__refcounts[string] <= 0:
            self.__counter += 1
            self.__corpus.remove(CorpusItem(string))
            del self.__refcounts[string]
            self.__lifecycle.item_removed(string)


class CorpusItem(object):
    def __init__(self, string):
        self.string = string

    def __hash__(self):
        return hash(self.string)

    def __cmp__(self, other):
        if len(self.string) < len(other.string):
            return -1
        if len(self.string) > len(other.string):
            return 1
        if self.string < other.string:
            return -1
        if self.string > other.string:
            return 1
        return 0

    def __eq__(self, other):
        return isinstance(other, CorpusItem) and self.__cmp__(other) == 0

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

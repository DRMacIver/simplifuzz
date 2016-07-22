# Simplifuzz

Simplifuzz is a new breed of fuzzer that works off a notion of 'label'. A label
is e.g. an AFL coverage target.

Simplifuzz attempts to produce a minimal element reaching each label. This
turns out to provide quite an impressive corpus.

This is all a work in progress. You may wish to ignore this repo for now.

## Interface

Simplifuzz starts from a classifier script and a set of initial examples. A
classifier takes its input on stdin and then prints a set of labels, one per
line, to stdout (labels may be arbitrary bytes but surrounding ascii whitespace
will be ignored).

It then proceeds to fuzz these, maintaining a corpus directory in
working/corpus with the full set of examples that the fuzz currently considers
to be "interesting".

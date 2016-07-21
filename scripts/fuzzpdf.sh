#!/usr/bin/env bash

set -x -e

cat > fuzz.pdf 

echo > remap

afl-showmap  -o remap -- pdftotext -q fuzz.pdf /dev/null

cat remap

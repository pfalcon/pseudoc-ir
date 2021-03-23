set -e

#PYTHON=python3
PYTHON="pycopy -X strict"

for f in tests/roundtrip/*.pseudoc; do
    echo $f

    $PYTHON -m pseudoc.parser $f > $f.out
    diff-hilite -u $f.exp $f.out
done

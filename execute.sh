#!/usr/bin/env bash
PYTHON_VERSION=`/usr/bin/env python -V 2>&1 | sed 's/.* //g' | sed 's/.[0-9]*$//g'`

PREFIX=/tmp/pybrig

if [ x$1 == "x" ]; then
    echo "Usage: execute.sh <trace> [prefix]"
    exit -1
fi

if [ x$2 != "x" ]; then
    PREFIX=$2
fi

SRCDIR=$PREFIX/src
ENVDIR=$PREFIX/env

echo "Sourcing configuration to: $SRCDIR"
echo "Installing libraries to: $ENVDIR"

if [ ! -e $1 ]; then
    echo "Trace file '$1' doesn't exist..."
    exit -1
fi

if [ ! -e "$ENVDIR/bin/bro" ]; then
    # Download / build dependencies we need to run stuff
    # Note: this only needs to be done once
    /usr/bin/env python configure.py --prefix=$ENVDIR --srcdir=$SRCDIR
else
    echo "Skipping configuration step (/tmp/pybrig/env appears to already exist)."
fi
export PYTHONPATH="$ENVDIR/lib/python$PYTHON_VERSION/site-packages:$ENVDIR/lib64/python$PYTHON_VERSION/site-packages"
export LD_LIBRARY_PATH=$ENVDIR/lib
# Execute the recorder daemon
/usr/bin/env python util/benchmark-snapshot.py > /tmp/snapshot.log 2> /tmp/snapshot.log&
# Execute the benchmark script
/usr/bin/env python benchmark.py --prefix=$ENVDIR -r $1
# Execute the information gathering script
/usr/bin/env python gather.py > /tmp/pybrig/trials/gather.json
# Tell the recorder daemon it can shut down
echo 'exit' > /tmp/benchmark.fifo
# Kill all processes that match the description of the recorder daemon ...
kill `ps | grep 'benchmark-snapshot' | grep -v 'grep' | gawk '{print $1}'` 2> /dev/null
# Package the results
/usr/bin/env python util/package.py


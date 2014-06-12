#!/usr/bin/env bash
PYTHON_VERSION=`/usr/bin/env python -V 2>&1 | sed 's/.* //g' | sed 's/.[0-9]*$//g'`

if [ x$1 == "x" ]; then
    echo "Usage: execute.sh <trace>"
    exit -1
fi

if [ ! -e $1 ]; then
    echo "Trace file '$1' doesn't exist..."
    exit -1
fi

if [ ! -e "/tmp/pybrig/env/bin/bro" ]; then
    # Download / build dependencies we need to run stuff
    # Note: this only needs to be done once
    /usr/bin/env python configure.py
else
    echo "Skipping configuration step (/tmp/pybrig/env appears to already exist)."
fi
export PYTHONPATH="/tmp/pybrig/env/lib/python$PYTHON_VERSION/site-packages:/tmp/pybrig/env/lib64/python$PYTHON_VERSION/site-packages"
export LD_LIBRARY_PATH=/tmp/pybrig/env/lib
# Execute the recorder daemon
/usr/bin/env python util/benchmark-snapshot.py > /tmp/snapshot.log 2> /tmp/snapshot.log&
# Execute the benchmark script
/usr/bin/env python benchmark.py -r $1
# Execute the information gathering script
/usr/bin/env python gather.py > /tmp/pybrig/gather.json
# Tell the recorder daemon it can shut down
echo 'exit' > /tmp/benchmark.fifo
# Kill all processes that match the description of the recorder daemon ...
kill `ps | grep 'benchmark-snapshot' | grep -v 'grep' | gawk '{print $1}'` 2> /dev/null


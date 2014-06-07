Motivational Blurb
------------------

One of the prerequisites of writing the (long, convoluted, exquisitely formatted) paper necessary to escape from college with a shiny
new graduate degree is to have some data available upon which to base said paper.  To this end, the PyBrIG toolkit is designed to
gather performance data from bro as it executes against a particular trace.

Note that this github project contains code only to handle the _collection_ of data.  It does not include code to visualize the
results.  For that code (and instructions on its use), please take a look at _TODO_.

Overview
--------

The Python Bro Information Gatherer (PyBrIG) project aims to automate the process of gathering system information and actually executing
a benchmark on a given system.  It aims to be cross-platform (targeted platforms are OSX 10.8+, FreeBSD 9+, and Linux 3.0+),
simple (a single wrapper script to launch a benchmark), and relatively self-contained.  Additionally, the code in here is intended to be
easily reusable / customizable for anyone interested in extending and / or replicating the benchmark process.

Architecture
------------

This project is divided into four different run-time components:

* configure.py - a convenience script that will download / build various dependencies for the benchmark.  Running this is not *required*,
but may serve to make the benchmark easier to start with than it otherwise would be.  Note that this script offers a way to download and
package scripts without actually installing them, and also offers a way to build from a pre-built package (e.g. in the event that a machine
is not connected to a network, the benchmark can still be configured and run).
* gather.py - a script that gathers as much system information as it is able to.  It makes calls to SIGAR (if present), psutil (if present),
puppet's facter binary (if present), sysctl, and lsmod.  Between these five libraries, it's possible to get a pretty complete picture of
a system.
* benchmark.py - a script that actually executes a benchmark on a system.  This injects a bro script that configures / runs various bits of
internal profiling to gather information about the running bro process and record it to a log.  The bro script also communicates with an
external process (via FIFO) that will record additional statistics about the program.
* util/benchmark-snapshot.py - the external entity that listens for commands to come in to a FIFO and records data.  This operates on
simple ASCII commands: 'init', 'record <PID> <network_time> <real_time>', 'close', and 'exit' are supported.

These four components are built on top of four small-ish libraries:

* benchmark.info.build - a wrapper that is able to download and build code from either git or .tar.(gz|bz2)
* benchmark.info.gather - a wrapper that abstracts a lot of the data collection into something reusable
* benchmark.info.trial - a wrapper that abstracts much of the details involved with running a single trial
* benchmark.prof.parse - a parser that offers a simple interface to dealing with prof.log data

benchmark.py could probably see a lot of its code refactored and pulled out into the library.

Stability Note
--------------

To work around issues with managing the recorder daemon as part of the benchmark process, starting that daemon has been moved into
its own step in the process below.  With that said, please keep an eye on /tmp/snapshot.log: if it goes too long without updates, it
could be that the bro process / python has lost the FIFO and can't get it back, which will cause the bro process to hang on write
once the FIFO buffer is full.

Requirements
------------

Building SIGAR bindings requires autoconf, automake, libtool, pkgconfig, Python headers (e.g. python2.7-devel), gcc, and make.

Building psutil requires a functional gcc toolchain to be present.

Please consult the bro documentation for an up-to-date explanation of what is required to successfully build the project on a given platform.

Executing all utilities (including configure.py) requires Python 2.6+ with a working installation of the 'sh' module
available.  If 'sh' is not present, try:

```bash
/usr/bin/env pip install sh
```

Running a Benchmark
-------------------

```bash
# Retrieve the relevant source code for this installation.
git clone https://github.com/cubic1271/pybrig ./pybrig
pushd pybrig
# Download / build dependencies we need to run stuff
# Note: this only needs to be done once
/usr/bin/env python configure.py
# s/X.Y/Python.Version/g
export PYTHONPATH=/tmp/pybrig/env/lib/pythonX.Y/site-packages:/tmp/pybrig/env/lib64/pythonX.Y/site-packages```
export LD_LIBRARY_PATH=/tmp/pybrig/env/lib
# Execute the information gathering script
/usr/bin/env python gather.py
# Execute the recorder daemon
/usr/bin/env python util/benchmark-snapshot.py > /tmp/snapshot.log 2> /tmp/snapshot.log&
# Execute the benchmark script
/usr/bin/env python benchmark.py
# Tell the recorder daemon it can shut down
echo 'exit' > /tmp/benchmark.fifo
```

Note that configure has a number of options to support packaging the dependencies necessary to run on a machine without
an available internet connection.

_TODO_: Example of how to configure on one machine to download packages, then move them to another box and execute there.

The results of the gather / benchmark scripts are generated in JSON format.  These results can be reviewed and e.g.
uploaded to something like ElasticSearch.

Uploading results
-----------------

There is a script provided at 'util/upload.py' which automates the upload of benchmark results to an ElasticSearch instance.  To use this script:

```bash
/usr/bin/env python util/upload.py      # to review a list of files that will be pushed onto an ES instance
/usr/bin/env python util/upload.py -e   # to actually *execute* the upload of the listed files
```

Privacy
-------

While the majority of the data included in the results of these benchmarks cannot be linked to a specific domain / machine,
there is *some* data that may be used in this fashion.  Specifically, the following information is included in the results
of a benchmark:

* Host interfaces (IPv4, IPv6, and MAC addresses for all interfaces)
* Hostnames
* Some trace statistics
* Partitions currently available on the machine (along with their filesystem type)

To help address this issue, a file is included here called 'privacy.conf'.  This file lists a number of regex-based filters
that are applied (as best as these utilities are able) to data generated by the tools that are run as part of the benchmark.

_NOTE_: Please review *all* configuration / benchmark results before uploading them.  privacy.conf is offered as a
convenience _only_, not as any kind of guarantee.

This file consists of a number of sections that appear as follows:

```
[X.include]
.*:.*
[X.exclude]
.*:.*
```

Each section of the above file [X.include, X.exclude] is defined to be a list of _Allow / Deny Rules_ that govern which pieces
of information are included in the output.  The portion on the left side of the ':' refers to the 'name' of the entry, and
the portion on the right side of the ':' is a regex that is applied to the 'value' of the entry.

Rules are applied in order, and _the last rule to match the name and / or value_ wins.  In the event an include and exclude
rule both match a particular piece of output, the _exclude_ rule takes precedence.  If _neither_ an include nor an exclude
rule matches an item, the item is _excluded_.

As an example, say we only wanted to include entries from sysctl that had 'ip' somewhere in the name.  Our rule set would be:

```
[sysctl.include]
.*ip.*:.*
[sysctl.exclude]
```

Alternatively, say we wanted to include entries from sysctl that had a value that began with '1'.  Our rule set would be:

```
[sysctl.include]
.*:1.*
[sysctl.exclude]
```

If we wanted entries from the 'ip' section of sysctl that had a value that started with '1', these rules could be combined:

```
[sysctl.include]
.*ip.*:1.*
[sysctl.exclude]
```

Note that the 'interfaces' section is a special one, and consists of the following keys:

* 'address': the IPv4 address of the interface
* 'address6': the IPv6 address of the interface
* 'hwaddr': the MAC address of the interface
* 'name': the name of the interface (e.g. 'eth0', 'en0')

Note that the above corresponds with the output of the 'interfaces' information as displayed by gather.py

Acknowledgments
---------------

* Robin Sommer for his continued guidance, assistance, and thoughtful feedback on this project.

Contributing
------------

TODO

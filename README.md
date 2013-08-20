Disclaimer
----------

This code is under very active development at the moment.  Do not use this code unless you know exactly what it is you are getting yourself into.

_You have been warned._

Motivational Blurb
------------------

One of the prerequisites of writing the (long, convoluted, exquisitely formatted) paper necessary to escape from college with a shiny new graduate degree is to have some data available upon which to base said paper.  To this end, the PyBrIG toolkit is designed to gather performance data from bro as it executes against a particular trace.  

Note that, by default, bro includes a number of scripts that are able to generate aggregate performance metrics, but most of these tools focus on general system performance metrics (e.g. how much CPU, how much memory) rather than trying to investigate *where* (in analyzer-land and script-land) bro is actually spending its time.  To remedy this, there is a forked version of bro that traces *all* the script code and *many* of the analyzers hit when processing a particular packet.  PyBrIG uses this forked version of bro to gather some very detailed information about how / where bro spends its time when executing a trace, and combines that with detailed process-level statistics (obtained on a regular basis via the Python psutil library) to generate a (hopefully) complete picture of how it was that bro spent its time processing a particular trace.

In the longer term, when enough of these benchmarks have been run against different traces on different systems, the idea is that some patterns may emerge with regard to where and how it is that bro spends its time in the general case.
  
Overview
--------

The Python Bro Information Gatherer (PyBrIG) project aims to automate the process of gathering system information and actually executing a benchmark on a given system.  It aims to be cross-platform (targeted platforms are OSX 10.6+, FreeBSD 8.1+, and Linux 2.6+), simple (a single wrapper script to launch a benchmark), and relatively self-contained.  Additionally, the code in here is intended to be easily reusable / customizeable for anyone interested in extending and / or replicating the benchmark process.

This project is divided into four sections:

* _Library Code_ -- Reusable code used to e.g. retrieve and build code and / or monitor a running bro instance.  Intended to be reusable.
* _Information Gathering_ -- Uses the _Library Code_ to actually gather information.  This code is largely specific to this particular benchmark.
* _Local Server_ -- Makes results available in handy REST form.  Also offers a place to upload results.  The REST API here is powered by python-eve.org, which is backed by (and requires) MongoDB in order to run.
* _Results Browser_ -- Client-side Javascript approach to rendering / exploring the results of a benchmark.  Depends on a _Local Server_ being available somewhere.

Requirements
------------

Building SIGAR bindings requires autoconf, automake, libtool, pkgconfig, Python headers (e.g. python2.7-devel), gcc, and make.

Building psutil requires a functional gcc toolchain to be present.

Please consult the bro documentation for an up-to-date explanation of what is required to successfully build the project on a given platform.

Executing the local REST / UI server requires a functional installation of MongoDB to be available.  Note that the location and username / password (if any) may be customized in the 'settings.py' file in the 'brig' module directory.

Executing the benchmark requires a functional installation of Python 2.6+ with a working installation of the 'sh' module available.  Additionally, processing the binary trace data requires a functional installation of Java (OpenJDK 1.7 should work fine) available on the path.

Execution
---------

The following is a condensed, hopefully more readable version of the execution script that ships with this library ('execute.sh').

```bash
# Retrieve the relevant source code for this installation.
git clone https://github.com/cubic1271/pybrig ./pybrig
pushd pybrig
# Download dependencies we need to run stuff
/path/to/python configure.py
export LD_LIBRARY_PATH=/tmp/pybrig/env/lib
# s/X.Y/Python.Version/g
export PYTHONPATH=/tmp/pybrig/env/lib/pythonX.Y/site-packages:/tmp/pybrig/env/lib64/pythonX.Y/site-packages
# Run the REST API (powered by EVE / Flask / MongoDB) and the UI
pushd bro/brig && /path/to/python server.py > /tmp/pybrig.server.log 2> /tmp/pybrig.server.err && popd
# Run the system information gathering script and upload the results to our local API
/path/to/python gather.py -u http://127.0.0.1/systems/
# Do a benchmark and upload the results to our local API
/path/to/python benchmark.py -c $1 -u http://127.0.0.1
# Launch a browser to view the results (we assume firefox is installed and on the system path):
firefox http://127.0.0.1/ui/index.html
```

Privacy
-------

While the majority of the data included in these traces is anonymous, there is *some* data that may be mapped to a specific machine and / or trace in some fashion.  Specifically, the following information is included in a benchmark:

* Host interfaces (IPv4, IPv6, and MAC addresses for all interfaces)
* Aggregate trace statistics (trace-summary results)
* Partitions currently available on the machine (along with their filesystem type)

Each script included with this project will eventually include a flag ('-P') which will do its best to not include any information that could be used to identify a particular system or site.  With that said, _please_ double check all output (the output of gather.py with no arguments, and also all files in /tmp/pybrig/trials generated after a benchmark)to ensure they meet any standards that may be applicable to your environment.

Contributing
------------

One of the really cool things about having a benchmarking toolkit is the ability to share results.  If you would like to do this:

* Ensure all benchmarks have been captured with the '-P' option enabled (see above).
* .tar.bz2 (or equivalent) the output of gather.py (specified via the '-o' option) and benchmark.py (/tmp/pybrig/trials) into a single, happy archive.
* Put a copy of the archive onto dropbox and / or an equivalent file-sharing service.
* Contact the individual / group in question to let them know :)

Thank you all in advance for your help and support!


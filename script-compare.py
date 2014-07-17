__author__ = 'clarkg1'

from optparse import OptionParser
import base64
import hashlib
import json
import os
import sh
import shutil
import sys
import uuid
import bro.benchmark.prof.info as prof_info
import bro.benchmark.info.trace as prof_trace

def script_sanitize(name):
    result = name.replace('/', '_')
    result = result.replace('.bro', '')
    return result

def trial_callback(trial):
    prof = prof_info.ProfileInfo(os.path.join(os.path.join(trial.basedir, trial.name), 'prof.log'))
    prof.process()
    prof_out = open(os.path.join(os.path.join(trial.basedir, trial.name), 'prof.json'), 'w')
    prof_out.write(prof.json())
    prof_out.close()

if __name__ == '__main__':
    prefix = "/tmp/pybrig/env"
    trial_dir = "/tmp/pybrig/trials"
    benchmark_id = uuid.uuid1()
    recorder_process = None

    parser = OptionParser()
    parser.add_option("-p", "--prefix", action="store", dest="prefix", help="Use packages from this directory path (NOTE: if non-standard, make sure your PYTHONPATH / LD_LIBRARY_PATH is correct...)", default=prefix, metavar="PREFIX")
    parser.add_option("-s", "--srcdir", action="store", dest="trial_dir", help="Results are stored at this location", default=trial_dir, metavar="STORAGE_DIR")
    parser.add_option("-f", "--file", action="store", dest="capture", help="Capture file to analyze", default=None, metavar="CAPTURE_FILE")
    parser.add_option("-r", "--read", action="store", dest="capture", help="Capture file to analyze (alias for '-f')", metavar="CAPTURE_FILE")
    (options, args) = parser.parse_args()

    if not options.capture:
        print "ERROR: No capture file specified"
        parser.print_help()
        sys.exit(-1)

    prefix = options.prefix
    trial_dir = options.trial_dir
    capture = options.capture
    capture = os.path.abspath(capture)

    try:
        os.makedirs(options.trial_dir)
    except OSError,ex:
        pass

    try:
        import psutil
    except ImportError:
        print "'psutil' could not be found.  Is your PYTHONPATH set?"
        sys.exit(-1)

    script_list = []

    script_list = args

    if len(script_list) == 0:
        print "No scripts provided as arguments to test.  Benchmark aborting ..."
        sys.exit(-1)

    broenv = os.environ.copy()
    if 'LD_LIBRARY_PATH' in broenv:
        broenv['LD_LIBRARY_PATH'] = broenv['LD_LIBRARY_PATH'] + ":" + prefix + '/lib'
    else:
        broenv['LD_LIBRARY_PATH'] = prefix + '/lib'

    import bro.benchmark.info.trial as bench
    benchmark_ref = bench.BenchmarkInfo()

    broexec = sh.Command(prefix + '/bin/bro').bake(_env=broenv)
    trial = bench.BenchmarkTrial(trial_dir, 'script-benchmark.bro', broexec,
                                 capture, scripts=['script-benchmark'], bare=False)

    tmp_list = []

    i = 1

    last_pct = 0

    # Scan the trace to get an idea of packet counts and distributions ...
    print "Scanning trace ..."

    ips_path = os.path.join(os.path.join(prefix, 'bin'), 'ipsumdump')
    info = prof_trace.TraceInfo(ips_path, options.capture)
    info.process()
    trace_info = open(os.path.join(trial.basedir, 'capture.json'), 'w')
    trace_info.write(info.json())
    trace_info.close()

    print "Duration: %s" % (info.duration)
    print "Packets: %s (%s pkt / sec)" % (info.count, info.count / info.duration)

    print "Total scripts to test: " + str(len(script_list))
    sys.stdout.write('Progress: ')
    sys.stdout.flush()

    try:
        for script in script_list:
            # print "Executing: loaded " + str(i) + " scripts out of " + str(len(script_list)) + "..."

            if( (i / float(len(script_list))) > (last_pct + 0.05) ):
                sys.stdout.write('=')
                sys.stdout.flush()
                last_pct += 0.05

            trial.name = 'load-' + str(i) + '-' + script_sanitize(script)
            tmp_list.append(script)
            data = dict()
            data['load_entries'] = tmp_list
            data['benchmark_log_path'] = '/tmp/benchmark.out'
            data['benchmark_output_delay'] = str(int(info.duration / info.resolution))

            try:
                trial.execute(trial.name, data, callback=trial_callback)
            except sh.ErrorReturnCode,ex:
                print "Trial failed to execute: " + str(ex.stderr)
                print "Output was: " + str(ex.stdout)
                print ex.message
                raise KeyboardInterrupt
            trial.pushd(os.path.join(trial.basedir, trial.name))
            shutil.copy(data['benchmark_log_path'], os.path.join(os.path.join(trial.basedir, trial.name), 'benchmark.json'))
            trial.popd()
            benchmark_ref.add(trial)
            i = i + 1
            # print ""

        print ""
        print "*** Done.  Data has been written to subdirectories of: %s" % trial.basedir
    except KeyboardInterrupt:
        print ""
        print "*** Benchmark aborted.  Current trial at time of termination: %s" % trial.name
        sys.exit(-1)

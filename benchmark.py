__author__ = 'clarkg1'

from optparse import OptionParser
import json
import os
import sh
import shutil
import sys
import uuid
import bro.benchmark.prof.parse as prof_parse

class TraceInfo(object):
    def __init__(self, binary, capture):
        self.capture = capture
        self.binary = binary
        self.resolution = 100.0

    def process(self):
        ips = sh.Command(self.binary).bake('-t')
        start_time = None
        end_time = None
        packet_count = 0
        for line in ips(self.capture):
            if line[0] == '!':
                continue
            packet_count += 1
            if not start_time:
                start_time = float(line)
            end_time = float(line)

        self.count = packet_count
        self.start = start_time
        self.end = end_time
        self.duration = end_time - start_time
        self.incr = self.duration / float(self.resolution)
        self.counters_list = list()
        trace_counters = dict()
        next_incr = start_time + self.incr
        trace_curr = start_time
        # 2nd pass to extract incremental protocol / packet counts at certain points
        # This is used to give us an idea of what kind of traffic we saw between times A and B
        for line in ips('-p', self.capture):
            if line[0] == '!':
                continue
            line = line.replace('\n', '')
            curr = line.split(' ')
            if float(curr[0]) >= next_incr:
                self.counters_list.append(trace_counters)
                trace_counters = dict()
                next_incr += self.incr
            if curr[1] not in trace_counters:
                trace_counters[curr[1]] = 0
            trace_counters[curr[1]] += 1

        # Scan our dict one last time to see if we ended outside of the exact interval ...
        do_append = False
        for item in trace_counters.keys():
            if trace_counters[item] != 0:
                do_append = True

        if do_append:
            self.counters_list.append(trace_counters)
        self.capture = self.capture.split('/')[-1]
        self.binary = self.binary.split('/')[-1]

    def json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class ProfileInfo(object):
    def __init__(self, path):
        self.log = prof_parse.ProfileLog(path)

    def process(self):
        self.data = list()
        for entry in self.log:
            self.data.append(entry)

    def json(self):
        # Don't want to include the log object in the output ...
        tlog = self.log
        del self.log
        rval = json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
        self.log = tlog
        return rval

def trial_callback(trial):
    prof = ProfileInfo(os.path.join(os.path.join(trial.basedir, trial.name), 'prof.log'))
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

    in_file_path = prefix + '/share/bro/base/init-default.bro'
    in_file = open(in_file_path, 'r')

    for line in in_file:
        if "@load" in line and "#" not in line:
            script_list.append(line.strip())

    in_file_path = prefix + '/share/bro/site/local.bro'
    in_file = open(in_file_path, 'r')

    for line in in_file:
        if "@load" in line and "#" not in line:
            script_list.append(line.strip())

    broenv = os.environ.copy()
    if 'LD_LIBRARY_PATH' in broenv:
        broenv['LD_LIBRARY_PATH'] = broenv['LD_LIBRARY_PATH'] + ":" + prefix + '/lib'
    else:
        broenv['LD_LIBRARY_PATH'] = prefix + '/lib'

    import bro.benchmark.info.trial as bench
    benchmark_ref = bench.BenchmarkInfo()

    broexec = sh.Command(prefix + '/bin/bro').bake(_env=broenv)
    trial = bench.BenchmarkTrial(trial_dir, 'script-benchmark.bro', broexec,
                                 capture, scripts=['script-benchmark'], bare=True)

    tmp_list = []

    i = 1

    last_pct = 0

    # Scan the trace to get an idea of packet counts and distributions ...
    print "Scanning trace ..."

    ips_path = os.path.join(os.path.join(prefix, 'bin'), 'ipsumdump')
    info = TraceInfo(ips_path, options.capture)
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

            trial.name = 'load-' + str(i)
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

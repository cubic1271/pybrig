from ConfigParser import ConfigParser
from optparse import OptionParser
import base64
import distutils
import hashlib
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

    def hash(self):
        hasher = hashlib.sha256()
        target = open(self.capture, 'rb')
        buf = target.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = target.read(65536)
        return base64.b64encode(hasher.digest())

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

        self.sha256 = self.hash()
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
    config_path = "benchmark.conf"

    parser = OptionParser()
    parser.add_option("-c", "--config", action="store", dest="config", help="Specify a path to a configuration file", default=config_path, metavar="CONFIG")
    parser.add_option("-p", "--prefix", action="store", dest="prefix", help="Use packages from this directory path (NOTE: if non-standard, make sure your PYTHONPATH / LD_LIBRARY_PATH is correct...)", default=prefix, metavar="PREFIX")
    parser.add_option("-s", "--srcdir", action="store", dest="trial_dir", help="Results are stored at this location", default=trial_dir, metavar="STORAGE_DIR")
    parser.add_option("-f", "--file", action="store", dest="capture", help="Capture file to analyze", default=None, metavar="CAPTURE_FILE")
    parser.add_option("-r", "--read", action="store", dest="capture", help="Capture file to analyze (alias for '-f')", metavar="CAPTURE_FILE")
    (options, args) = parser.parse_args()
    
    config_entries = ConfigParser(allow_no_value=True)
    config_entries.optionxform = str
    config_entries.read(config_path)

    prefix = options.prefix
    trial_dir = options.trial_dir
    
    if options.capture:
        capture = options.capture
        capture = [os.path.abspath(capture)]
    else:
        capture = config_entries.items('captures')
        tcapture = []
        for item in capture:
            item = item[0]
            item = os.path.expanduser(item)
            tcapture.append(os.path.abspath(item))
        capture = tcapture

    use_bare_mode = False
    for entry in config_entries.items('options'):
        if entry[0] == 'bare_mode':
            if entry[1].lower() == 'true':
                use_bare_mode = True
    print "Bare mode: " + str(use_bare_mode)
    
    print "Running with capture(s):"
    for item in capture:
        print "  > " + item
    print ""

    try:
        os.makedirs(options.trial_dir)
    except OSError,ex:
        pass

    broenv = os.environ.copy()
    if 'LD_LIBRARY_PATH' in broenv:
        broenv['LD_LIBRARY_PATH'] = broenv['LD_LIBRARY_PATH'] + ":" + prefix + '/lib'
    else:
        broenv['LD_LIBRARY_PATH'] = prefix + '/lib'

    broenv['BRO_PLUGIN_ACTIVATE'] = 'Instrumentation::Instrumentation'

    import bro.benchmark.info.trial as bench
    benchmark_ref = bench.BenchmarkInfo()

    broexec = sh.Command(prefix + '/bin/bro').bake(_env=broenv)
    for entry in capture:
        trial = bench.BenchmarkTrial(trial_dir, 'script-benchmark.bro', broexec,
                                     entry, scripts=['script-benchmark'], bare=use_bare_mode)

        script_list = []
        tmp_list = []
        if 'scripts-base' in config_entries.sections():
            for script in config_entries.items('scripts-base'):
                tmp_list.append('@load ' + script[0])

        # Scan the trace to get an idea of packet counts and distributions ...
        print "Scanning trace ..."

        ips_path = os.path.join(os.path.join(prefix, 'bin'), 'ipsumdump')
        info = TraceInfo(ips_path, entry)
        info.process()
        trace_info = open(os.path.join(trial.basedir, 'capture.' + os.path.split(entry)[-1] + '.json'), 'w')
        trace_info.write(info.json())
        trace_info.close()

        print "Duration: %s" % (info.duration)
        print "Packets: %s (%s pkt / sec)" % (info.count, info.count / info.duration)

        try:
            trial_list = []
            for section in config_entries.sections():
                if 'trial-' in section:
                    trial_list.append(section)
            
            i = 1
            for entry in trial_list:
                # print "Executing: loaded " + str(i) + " scripts out of " + str(len(script_list)) + "..."
                print "Executing trial " + str(i) + " / " + str(len(trial_list)) + "..."
                scripts = config_entries.items('trial-' + str(i))
                trial.name = 'load.' + str(i) + '.' + entry
                for script in scripts:
                    tmp_list.append('@load ' + script[0])
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
                benchmark_ref.add(trial)
                i = i + 1
                # print ""

            print ""
            print "*** Done.  Data has been written to subdirectories of: %s" % trial.basedir
        except KeyboardInterrupt:
            print ""
            print "*** Benchmark aborted.  Current trial at time of termination: %s" % trial.name
            sys.exit(-1)


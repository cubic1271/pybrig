__author__ = 'clarkg1'

from optparse import OptionParser
import json
import os
import sh
import sys
import uuid

def do_upload(files, urls):
    combined = zip(files, urls)
    running = []
    for curr, url in combined:
        curr_uuid = str(uuid.uuid4())
        print "Uploading: " + os.path.realpath(curr) + " to " + url
        in_file = open(curr, 'r')
        payload = "data=" + in_file.read()
        tmp_file = open('/tmp/pybrig.' + curr_uuid + '.benchmark.upload', 'w')
        tmp_file.write(payload)
        tmp_file.close()
        running.append(sh.curl('-X', 'POST', url, '-d', '@/tmp/pybrig.' + curr_uuid + '.benchmark.upload', _bg=True))
        in_file.close()

    for entry in running:
        entry.wait()

    sh.rm('-f', sh.glob('/tmp/pybrig.*'))

if __name__ == '__main__':
    prefix = "/tmp/pybrig/env"
    trial_dir = "/tmp/pybrig/trials"
    benchmark_id = uuid.uuid1()
    jbropan_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib/jbropan.jar")

    java = sh.Command('java')

    parser = OptionParser()
    parser.add_option("-p", "--prefix", action="store", dest="prefix", help="Use packages from this directory path (NOTE: if non-standard, make sure your PYTHONPATH / LD_LIBRARY_PATH is correct...)", default=prefix, metavar="PREFIX")
    parser.add_option("-s", "--srcdir", action="store", dest="trial_dir", help="Results are stored at this location", default=trial_dir, metavar="STORAGE_DIR")
    parser.add_option("-c", "--capture-file", action="store", dest="capture", help="Capture file to analyze", default=None, metavar="CAPTURE_FILE")
    parser.add_option("-I", "--id", action="store", dest="uuid", help="uuid of system object with which to associate this benchmark", default=None, metavar="UUID")
    parser.add_option("-j", "--jbropan", action="store", dest="jbropan", help="Location of jbropan.jar (used to post-process trace output", default=jbropan_path, metavar="JBROPAN_PATH")
    parser.add_option("-u", "--upload", action="store", dest="upload", help="URL used to upload results of the benchmark.", default=None, metavar="UPLOAD_PATH")
    parser.add_option("-U", "--upload-only", action="store_true", dest="upload_only", help="If true, *only* upload results of a previous benchmark (don't actually run anything)", default=False)
    (options, args) = parser.parse_args()

    if os.getenv("LD_LIBRARY_PATH", None) and os.getenv("LD_LIBRARY_PATH", None) != os.path.join(options.prefix, '/lib'):
        print "WARNING: Your LD_LIBRARY_PATH does not include '" + os.path.join(options.prefix, '/lib') + "'.  If this path is non-standard, certain imported libraries may not work properly."

    if not os.path.exists(jbropan_path) and not options.upload_only:
        print "Unable to find jbropan.jar (used to post-process trace output and transform it into .json files).  Please re-run this script with the '-j' option."
        print "Path was: " + jbropan_path
        sys.exit(1)

    prefix = options.prefix
    trial_dir = options.trial_dir
    capture = options.capture

    if not capture and not options.upload_only:
        print "A capture file must be specified.  Please re-run this script with the '-c' option."
        sys.exit(1)

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
    broenv['LD_LIBRARY_PATH'] = prefix + '/lib'

    import bro.benchmark.info.trial as bench

    benchmark_ref = bench.BenchmarkInfo()

    broexec = sh.Command(prefix + '/bin/bro').bake(_env=broenv)

    trial = bench.BenchmarkTrial(trial_dir, 'script-benchmark.bro', broexec,
                                 capture, scripts=['script-benchmark'], bare=True)

    if not options.upload_only:
        tmp_list = []

        i = 1

        last_pct = 0

        sys.stdout.write('Scripts: ')
        sys.stdout.flush()

        for script in script_list:
            # print "Executing: loaded " + str(i) + " scripts out of " + str(len(script_list)) + "..."

            if( (i / float(len(script_list))) > (last_pct + 0.1) ):
                sys.stdout.write('=')
                sys.stdout.flush()
                last_pct += 0.1

            trial.name = 'load-' + str(i)
            tmp_list.append(script)
            data = dict()
            data['map_out'] = os.path.join(os.path.join(trial.basedir, trial.name), 'trace.map')
            data['trace_out'] = os.path.join(os.path.join(trial.basedir, trial.name), 'trace.out')
            data['load_entries'] = tmp_list

            trial.execute(trial.name, data)
            java('-jar', jbropan_path, '-m', data['map_out'], '-t', data['trace_out'], '-o', os.path.join(trial.basedir, trial.name), '-J', '-T', trial.uuid)
            os.unlink(data['map_out'])
            os.unlink(data['trace_out'])
            trial.pushd(os.path.join(trial.basedir, trial.name))
            out_file = open('trial.json', 'w')
            out_file.write(trial.json())
            out_file.close()
            trial.popd()
            benchmark_ref.add(trial)
            i = i + 1

        print ""

        trial = bench.BenchmarkTrial(trial_dir, 'connection-drop.bro', broexec,
                                        capture, scripts=['connection-drop'])

        sys.stdout.write("Drop: ")
        sys.stdout.flush()

        last_pct = 0.0

        for i in range(0, 101, 5):
            if( (i / 100.0) > (last_pct + 0.1) ):
                sys.stdout.write('=')
                sys.stdout.flush()
                last_pct += 0.1

            trial.name = 'drop-' + str(i)
            data = dict()
            data['ratio'] = i / 100.0
            data['map_out'] = os.path.join(os.path.join(trial.basedir, trial.name), 'trace.map')
            data['trace_out'] = os.path.join(os.path.join(trial.basedir, trial.name), 'trace.out')

            trial.execute(trial.name, data)
            java('-jar', jbropan_path, '-m', data['map_out'], '-t', data['trace_out'], '-o', os.path.join(trial.basedir, trial.name), '-J', '-T', trial.uuid)
            os.unlink(data['map_out'])
            os.unlink(data['trace_out'])
            trial.pushd(os.path.join(trial.basedir, trial.name))
            out_file = open('trial.json', 'w')
            out_file.write(trial.json())
            out_file.close()
            trial.popd()
            benchmark_ref.add(trial)

        trial.pushd(trial.basedir)
        out_file = open("benchmark.json", 'w')
        out_file.write(benchmark_ref.json())
        out_file.close()
        trial.popd()

    if options.upload:
        trial.pushd(trial.basedir)
        bench_file = open('benchmark.json', 'r')
        benchmarks = json.load(bench_file)
        bench_file.close()
        do_upload(['benchmark.json'], [options.upload + '/benchmarks/'])

        for entry in benchmarks['trials']:
            trial.pushd(os.path.join(trial.basedir, entry['name']))
            do_upload(['call_chain.json', 'packet_chain.json', 'count.json', 'event_path.json', 'script_timing.json', 'trial.json', 'map.json'],
                [options.upload + '/call_chains/', options.upload + '/packet_chains/', options.upload + '/counts/', options.upload + '/event_paths/',
                 options.upload + '/script_timings/', options.upload + '/sys_profile_entries/', options.upload + '/mappings/'])
#            requests.post('', data=payload)
            trial.popd()

    print ""

    print "Done."

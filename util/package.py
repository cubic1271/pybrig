import bz2
import json
import optparse
import os
import shutil
import sys

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-t", "--trial-path", action="store", dest="trial_path", help="Path to the output from a benchmark run", default="/tmp/pybrig/trials")

    (options, args) = parser.parse_args()

    trial_base = options.trial_path
    user = None
    pwd = None

    entries = os.listdir(trial_base)

    output_aggregator = dict()

    if 'gather.json' not in entries:
        print "[ERROR] Invalid trial directory: unable to find 'gather.json' in directory contents."
        print "[ERROR] Path was %s" % trial_base
        sys.exit(-1)
    
    if 'capture.json' not in entries:
        print "[ERROR] Invalid trial directory: unable to find 'capture.json' in directory contents."
        print "[ERROR] Path was: %s" % trial_base
        sys.exit(-1)

    curr = open(os.path.join(trial_base, 'capture.json'), 'r')
    output_aggregator['system-info'] = json.load(curr)
    curr = open(os.path.join(trial_base, 'gather.json'), 'r')
    output_aggregator['gather-info'] = json.load(curr)

    for entry in entries:
        if not os.path.isdir(os.path.join(trial_base, entry)):
            continue
        curr_trial = os.path.join(trial_base, entry)
        benchmark = os.path.join(curr_trial, 'benchmark.json')
        profile = os.path.join(curr_trial, 'prof.json')
        if not os.path.exists(benchmark):
            print "[WARN] Malformed trial result - missing benchmark.json (%s)" % benchmark
            continue
        if not os.path.exists(profile):
            print "[WARN] Malformed trial result - missing prof.json (%s)" % profile
            continue        

        output_aggregator[entry] = dict()
        curr = open(benchmark, 'r')
        output_aggregator[entry]['benchmark'] = json.load(curr)
        curr = open(profile, 'r')
        output_aggregator[entry]['profile'] = json.load(curr)

    output_file = bz2.BZ2File('benchmark-output.bz2', 'wb')
    json.dump(output_aggregator, output_file, sort_keys=True, indent=4)


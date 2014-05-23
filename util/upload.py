import getpass
import optparse
import os
import sh
import sys

class Curl(object):
    pass

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-e", "--execute", action="store_true", dest="execute", help="Actually upload files to host", default=False)
    parser.add_option("-u", "--url", action="store", dest="url", help="Destination host (defaults to 'http://127.0.0.1:9200')", default='http://127.0.0.1:9200', metavar='URL')
    parser.add_option("-t", "--trial-path", action="store", dest="trial_path", help="Path to the output from a benchmark run", default="/tmp/pybrig/trials")
    parser.add_option("-s", "--sysdata-path", action="store", dest="sysdata_path", help="Path to the output from gather.py", default=None)
    parser.add_option("-a", "--basic-auth", action="store_true", dest="auth", help="Prompt for credentials and forward as HTTP basic", default=False)
    parser.add_option("-i", "--target-index", action="store", dest="index", help="Upload results to the ES index specified here", default="benchmark")
    
    (options, args) = parser.parse_args()

    target = options.url
    index_name = options.index
    file_mapping = dict({'benchmark.json':'benchmark', 'prof.json':'profile'})
    trial_base = options.trial_path
    sysdata_path = options.sysdata_path

    entries = os.listdir(trial_base)
    file_list = []

    if sysdata_path:
        if not os.path.exists(sysdata_path):
            print "[ERROR] No system data found at location: %s" % sysdata_path
            sys.exit(-1)
        file_list.append(sysdata_path)

    if 'capture.json' not in entries:
        print "[ERROR] Invalid trial directory: unable to find 'capture.json' in directory contents."
        print "[ERROR] Path was: %s" % trial_base
        sys.exit(-1)

    file_list.append(os.path.join(trial_base, 'capture.json'))
    uploads = dict()

    for entry in entries:
        if not os.path.isdir(os.path.join(trial_base, entry)):
            continue
        curr_trial = os.path.join(trial_base, entry)
        benchmark = os.path.join(curr_trial, 'benchmark.json')
        profile = os.path.join(curr_trial, 'prof.json')
        if not os.path.exists(benchmark):
            print "[WARN] Malformed trial result - missing benchmark.json (%s)" % benchmark
        if not os.path.exists(profile):
            print "[WARN] Malformed trial result - missing prof.json" % profile
        file_list.append(benchmark)
        file_list.append(profile)
        uploads[entry] = (benchmark, profile)

    print "** Files to upload: "

    for entry in file_list:
        print entry

    if not options.execute:
        print "Re-execute this script with the -e option to actually upload the above files."
        sys.exit(0)

    if not options.execute:
        sys.exit(0)

    if options.auth:
        user = getpass.getuser()
        pwd = getpass.getpass()

    curl = Curl()
    curl.put = sh.Command('curl').bake('-XPUT', '-H', 'Content-Type: application/json')
    curl.delete = sh.Command('curl').bake('-XDELETE', '-H', 'Content-Type: application/json')

    index_path = '%s/%s' % (target, index_name)
    print "Clearing old index ..."
    curl.delete(index_path)

    print "Creating new index ..."
    curl.put(index_path)

    if sysdata_path:
        print "Uploading system info ..."
        curl.put('-d', '@%s' % file_list[0], '%s/%s/%s' % (index_path, 'system', 'info'))
        del file_list[0]

    print "Uploading capture info ..."
    curl.put('-d', '@%s' % file_list[0], '%s/%s/%s' % (index_path, 'capture', 'info'))

    del file_list[0]

    for entry in file_list:
        tmp = os.path.split(entry)
        upload_target = file_mapping[tmp[1]]
        type_target = os.path.split(tmp[0])[1]
        print "Uploading %s/%s" % (type_target, upload_target)
        res = curl.put('-d', '@%s' % entry, '%s/%s/%s' % (index_path, type_target, upload_target))
        print res

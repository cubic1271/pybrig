import getpass
import optparse
import os
import sh
import shutil
import sys

class CurlConfig(object):
    def __init__(self, executing=False, user=None, pwd=None):
        self.user = user
        self.pwd = pwd
        self.output = []
        self.desc = []

    def request(self, url, method, path=None):
        coutput = ""
        coutput += "url = %s\nrequest = %s\nheader = \"Content-Type:application/json\"\n" % (url, method)
        if path:
            coutput += "data = @%s\n" % path
        if self.user and self.pwd:
            coutput += "user = %s:%s\n" % (self.user, self.pwd)
        elif self.user:
            coutput += "user = %s\n" % self.user
        coutput += "\n"
        self.output.append(coutput)
        self.desc.append("%s %s [@%s]" % (method, url, path))

    def put(self, url, path):
        self.request(url, "PUT", path=path)

    def delete(self, url):
        self.request(url, "DELETE")

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-e", "--execute", action="store_true", dest="execute", help="Actually upload files to host", default=False)
    parser.add_option("-u", "--url", action="store", dest="url", help="Destination host (defaults to 'http://127.0.0.1:9200')", default='http://127.0.0.1:9200', metavar='URL')
    parser.add_option("-t", "--trial-path", action="store", dest="trial_path", help="Path to the output from a benchmark run", default="/tmp/pybrig/trials")
    parser.add_option("-s", "--sysdata-path", action="store", dest="sysdata_path", help="Path to the output from gather.py", default=None)
    parser.add_option("-a", "--basic-auth", action="store_true", dest="auth", help="Prompt for credentials and forward as HTTP basic", default=False)
    parser.add_option("-i", "--target-index", action="store", dest="index", help="Upload results to the ES index specified here", default="benchmark")
    parser.add_option('-d', "--dump-contents", action="store_true", dest="dump", help="Dump contents of all listed files to stdout", default=False)

    (options, args) = parser.parse_args()

    target = options.url
    index_name = options.index
    file_mapping = dict({'benchmark.json':'benchmark', 'prof.json':'profile'})
    trial_base = options.trial_path
    sysdata_path = options.sysdata_path
    user = None
    pwd = None

    if options.auth:
        user = raw_input("User:")
        if options.execute:
            pwd = getpass.getpass("Password:")

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

    if options.dump:
        for entry in file_list:
            with open(entry, 'r') as f:
                shutil.copyfileobj(f, sys.stdout)

    curl = CurlConfig(user=user, pwd=pwd)

    index_path = '%s/%s' % (target, index_name)
    curl.delete(index_path)

    curl.put(index_path, None)

    if sysdata_path:
        curl.put('%s/%s/%s' % (index_path, 'system', 'info'), file_list[0])
        del file_list[0]

    curl.put('%s/%s/%s' % (index_path, 'capture', 'info'), file_list[0])

    del file_list[0]

    for entry in file_list:
        tmp = os.path.split(entry)
        upload_target = file_mapping[tmp[1]]
        type_target = os.path.split(tmp[0])[1]

        curl.put('%s/%s/%s' % (index_path, type_target, upload_target), entry)

    if not options.execute and not options.dump:
        for desc in curl.desc:
            print desc
        print "Re-execute this script with -e to execute the above via curl..."

    if options.dump or not options.execute:
        sys.exit(0)

    for item,desc in zip(curl.output, curl.desc):
        print desc
        sh.curl('-K', '-', _in=item)

import bro.benchmark.info.gather as gather

from optparse import OptionParser

import re
import sh
import uuid

__author__ = 'clarkg1'

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-o", "--output", action="store", dest="output", help="Write gathered information to OUTPUT.  If this is not specified, stdout is used.", default=None, metavar="OUTPUT")
    parser.add_option("-u", "--upload", action="store", dest="upload", help="Upload gathered system information to URL.  If this is specified, no output is written locally unless -o is specified as well.", default=None, metavar="UPLOAD")
    (options, args) = parser.parse_args()

    info = gather.SystemInformation()
    info.gather()

    if options.output:
        out_file = open(options.output, 'w')
        out_file.write(info.json())
        out_file.close()

    if options.upload:
        # we need to run through the sysctl data and transform our keys, since mongodb doesn't allow for dots in the
        # key name.
        tmpsys = dict()
        for key in info.sysctl.keys():
            currkey = re.sub('\\.', '/', key)
            tmpsys[currkey] = info.sysctl[key]
        info.sysctl = tmpsys
        tmpfile = 'pybrig.gather.' + str(uuid.uuid4()) + '.tmp'
        out_file = open(tmpfile, 'w')
        out_file.write('data = ')
        out_file.write(info.json())
        out_file.close()
        res = sh.curl('-X', 'POST', options.upload, '-d', '@' + tmpfile)
        print res.stdout
        print res.stderr
        sh.rm('-f', tmpfile)

    if not options.upload and not options.output:
        print info.json()

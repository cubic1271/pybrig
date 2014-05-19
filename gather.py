import bro.benchmark.info.gather as gather

from optparse import OptionParser

import re
import sh
import uuid

__author__ = 'clarkg1'

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-o", "--output", action="store", dest="output", help="Write gathered information to OUTPUT.  If this is not specified, stdout is used.", default=None, metavar="OUTPUT")
    (options, args) = parser.parse_args()

    matcher = gather.ExcludeInfoMatcher()

    info = gather.SystemInformation()
    info.gather()

    if options.output:
        out_file = open(options.output, 'w')
        out_file.write(info.json())
        out_file.close()

    if not options.output:
        print info.json()

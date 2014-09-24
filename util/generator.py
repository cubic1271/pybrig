from optparse import OptionParser


if __name__ == '__main__':
    prefix = '/tmp/pybrig/env'

    parser = OptionParser()
    parser.add_option("-p", "--prefix", action="store", dest="prefix", help="Search for scripts in this path", default=prefix, metavar="PREFIX")
    (options, args) = parser.parse_args()

    script_list = []

    in_file_path = prefix + '/share/bro/base/init-default.bro'
    in_file = open(in_file_path, 'r')

    for line in in_file:
        if "@load" in line and "#" not in line:
            script_list.append(line.strip())

    in_file_path = prefix + '/share/bro/site/local.bro'
    in_file = open(in_file_path, 'r')

    for line in in_file:
        if "@load" in line and "#" not in line and '@load-sigs' not in line:
            script_list.append(line.strip())

    print "[scripts-base]"

    is_current_base = True
    index = 2

    while is_current_base:
        if "base/" not in script_list[0]:
            is_current_base = False
            print ""
            print "[trial-1]"
        print script_list[0].replace('@load ', '')
        del script_list[0]

    for item in script_list:
        print ""
        print "[trial-" + str(index) + "]"
        print item.replace('@load ', '')
        index += 1

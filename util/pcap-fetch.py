#!/usr/bin/env python
import cmd
import sh
import sys
import urllib2

class PcapSource(object):
    def __init__(self, url, description):
        self.url = url
        self.description = description
        self.name = self.url.split('/')[-1]

pcaplist = [PcapSource('http://www.bro.org/static/traces/2009-M57-day11-18.trace.gz', 'Part of the M57 trace collection'),
            PcapSource('http://www.bro.org/static/traces/2009-M57-day11-21.trace.gz', 'Part of the M57 trace collection'),
            PcapSource('http://www.bro.org/static/traces/ipv6.trace.gz', 'Example IPv6 trace'),
            PcapSource('http://2009.hack.lu/archive/2009/InfoVisContest/jubrowska-capture_1.cap', 'Information Security Visualization Contest - hack.lu 2009')]

class PcapFetchPrompt(cmd.Cmd):
    def __init__(self):
        cmd.Cmd.__init__(self)

    def do_ls(self, arg):
        """Alias for 'list'"""
        self.do_list(arg)

    def do_list(self, arg):
        """List of available packet captures"""
        for capture in pcaplist:
            print "%s - %s  [%s]" % (capture.name, capture.description, capture.url)

    def do_EOF(self, arg):
        """Handler for EOF event"""
        print ""
        self.do_exit(arg)

    # Credit: http://stackoverflow.com/questions/22676/how-do-i-download-a-file-over-http-using-python
    def do_fetch(self, arg):
        """Fetches a particular packet capture"""
        target = None
        if not arg:
            print "Usage: 'fetch <name-of-capture>'"
        for capture in pcaplist:
            if capture.name == arg:
                target = capture.url
        if not target:
            print "No such capture: %s" % arg
            return

        try:
            file_name = target.split('/')[-1]
            u = urllib2.urlopen(target)
            f = open(file_name, 'wb')
            meta = u.info()
            file_size = int(meta.getheaders("Content-Length")[0])
            print "Saving to: %s   [%s MB]" % (file_name, int(100 * file_size / 1024.0 / 1024.0) / 100.0)

            file_size_dl = 0
            block_sz = 65536
            while True:
                buffer = u.read(block_sz)
                if not buffer:
                    break

                file_size_dl += len(buffer)
                f.write(buffer)
                status = "\rRetrieved: %10dM  [%3.2f%%]\r" % (file_size_dl / 1024 / 1024, file_size_dl * 100. / file_size)
                status = status + chr(8)*(len(status)+1)
                sys.stdout.write(status)

            f.close()
            print ""
            print "Fetch completed!"
        except KeyboardInterrupt:
            print ""
            print "Fetch aborted!"

    def do_quit(self, arg):
        """Exits this prompt"""
        self.do_exit(arg)

    def do_exit(self, arg):
        """Exits this prompt"""
        sys.exit(0)

if __name__ == '__main__':
    prompt = PcapFetchPrompt()
    prompt.prompt = 'pcap-fetch> '
    while True:
        try:
            prompt.cmdloop('List all available captures by entering "list", or fetch a particular capture by using "fetch"')
        except KeyboardInterrupt:
            print ""
            print "Exiting on CTRL-C..."
            sys.exit(0)

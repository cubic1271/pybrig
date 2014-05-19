__author__ = 'clarkg1'

import os
import json
import optparse
import shutil
import sys
try:
    import psutil
except ImportError:
    print "WARN: could not import psutil"
    sys.exit(-1)
import time

class MonitorEntry(object):
    pass

class MonitorExecutor(object):
    def __init__(self):
        self.entry = dict()

    def safe_psutil_measure(self, fptr):
        try:
            return fptr()
        except psutil.AccessDenied:
            return None

    def update(self, pid, ts, base):
        entry = MonitorEntry()
        process = psutil.Process(pid)
        entry.ts = ts
        entry.pid = pid
        entry.cmd = " ".join(process.cmdline())
        entry.sent = base
        entry.start = time.time()
        entry.memory =  self.safe_psutil_measure(psutil.virtual_memory)
        entry.swap = self.safe_psutil_measure(psutil.swap_memory)
        entry.cpu = self.safe_psutil_measure(psutil.cpu_times)
        entry.disk = self.safe_psutil_measure(psutil.disk_io_counters)
        entry.pmem = self.safe_psutil_measure(process.get_ext_memory_info)
        if hasattr(process, 'get_io_counters'):
            entry.pdisk = self.safe_psutil_measure(process.get_io_counters)
        else:
            entry.pdisk = dict()
        entry.pcpu = self.safe_psutil_measure(process.get_cpu_times)
        entry.pthreads = self.safe_psutil_measure(process.get_threads)
        entry.ctx = self.safe_psutil_measure(process.get_num_ctx_switches)
        # NOTE: This call is unsafe on OS/X.
        # entry.mmaps = self.safe_psutil_measure(process.get_memory_maps)
        entry.lag = entry.start - entry.sent
        self.entry = entry

    def json(self):
        # Note: this includes nicely-formatted JSON.  This is good for debugging, but bad for file size.
        #return json.dumps(self.entry, default=lambda o: o.__dict__, sort_keys=True, indent=4)
        return json.dumps(self.entry, default=lambda o: o.__dict__, sort_keys=True)

class SnapshotConfig(object):
    fifo = None
    path = None
    channel_in = None
    channel_out = None
    pid_file = "/tmp/benchmark.pid"

class SnapshotCommands(object):
    first_entry = True
    # A no-op to help us make sure things are set up correctly.
    @staticmethod
    def do_hi(cmd):
        pass

    @staticmethod
    def do_init(cmd):
        print str(time.time()) + " [INFO] initializing file at " + SnapshotConfig.path
        SnapshotConfig.first_entry = True
        SnapshotConfig.channel_out.seek(0)
        SnapshotConfig.channel_out.truncate()
        SnapshotConfig.channel_out.write('"data" : [')
        SnapshotConfig.channel_out.flush()

    @staticmethod
    def do_record(cmd):
        print str(time.time()) + " [INFO] recording data to " + SnapshotConfig.path
        if len(cmd) != 4:
            sys.stderr.write(str(time.time()) + ' [ERROR] Bad `record` command: ' + str(cmd) + '\n')
            return
        monitor = MonitorExecutor()
        try:
            monitor.update(int(cmd[1]), float(cmd[2]), float(cmd[3]))
            if not SnapshotConfig.first_entry:
                SnapshotConfig.channel_out.write(', ')
            else:
                SnapshotConfig.first_entry = False
            SnapshotConfig.channel_out.write(monitor.json() + '\n')
        except psutil.AccessDenied:
            sys.stderr.write(str(time.time()) + ' [ERROR] Unable to open process - access denied\n')
        except RuntimeError:
            sys.stderr.write(str(time.time()) + ' [ERROR] Runtime error.\n')

    @staticmethod
    def do_close(cmd):
        print str(time.time()) + " [INFO] closing file at " + SnapshotConfig.path
        SnapshotConfig.channel_out.write(']')
        SnapshotConfig.channel_out.flush()

    @staticmethod
    def do_exit(cmd):
        print str(time.time()) + " [INFO] exiting ..."
        SnapshotConfig.channel_out.close()
        SnapshotConfig.channel_in.close()

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-f", "--file", action="store", dest="path", help="File to which we'd like to append output", default="/tmp/benchmark.out", metavar="LOG")
    parser.add_option("-r", "--read", action="store", dest="fifo", help="File from which we'd like to read commands", default="/tmp/benchmark.fifo", metavar="FIFO")

    (options, args) = parser.parse_args()

    SnapshotConfig.fifo = options.fifo
    SnapshotConfig.path = options.path

    if os.path.exists(SnapshotConfig.pid_file):
        pid_check = open(SnapshotConfig.pid_file, 'r')
        cpid = pid_check.readline()
        running = False
        # Send signal 0 to see if the pid is running ...
        try:
            os.kill(int(cpid), 0)
            running = True
        except OSError:
            pass
        pid_check.close()
        if running:
            sys.stderr.write('%s [ERROR] Process already running: %s\n' % (time.time(), cpid))
            sys.exit(-1)
        else:
            print str(time.time()) + ' [INFO] Cleaning up stale PID file ...'
            os.remove(SnapshotConfig.pid_file)

    pid_out = open(SnapshotConfig.pid_file, 'w')
    pid_out.write(str(os.getpid()))
    pid_out.close()

    print "%s [INFO] Process (%s) spinning up ..." % (time.time(), os.getpid())

    if not os.path.exists(options.fifo):
        print "%s [INFO] Creating new FIFO at %s" % (time.time(), options.fifo)
        os.mkfifo(options.fifo)

    try:
        SnapshotConfig.channel_out = open(options.path, 'a')
        SnapshotConfig.channel_in = open(options.fifo, 'r')
        res = "hi"
        while res != None:
            res = SnapshotConfig.channel_in.readline()
            if res == "":
                print "%s [INFO] Reached EOF.  Re-opening FIFO ..." % time.time()
                SnapshotConfig.channel_in = open(options.fifo, 'r')
                continue
            res = res.replace('\n', '')
            cmd = res.split(' ')
            if hasattr(SnapshotCommands, 'do_' + cmd[0]):
                getattr(SnapshotCommands, 'do_' + cmd[0])(cmd)
            else:
                sys.stderr.write(str(time.time()) + " [ERROR] Bad command: " + str(cmd) + "\n")
                continue
    except KeyboardInterrupt:
        print "%s [INFO] Shutting down on user request (CTRL-C) ..." % time.time()

    os.remove(SnapshotConfig.pid_file)
    sys.exit(0)

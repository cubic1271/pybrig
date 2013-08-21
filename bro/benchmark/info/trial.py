__author__ = 'clarkg1'

from mako.template import Template

import json
import os
import psutil
import sh
import threading
import time
import uuid

class TrialInfo(object):
    def __init__(self, uuid, name):
        self.uuid = uuid
        self.name = name

class BenchmarkInfo(object):
    def __init__(self, system_uuid=None):
        self.uuid = str(uuid.uuid4())
        self.time = time.time()
        self.system_uuid = system_uuid
        self.trials = []

    def add(self, trial):
        self.trials.append(TrialInfo(str(trial.uuid), trial.name))

    def json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class MonitorEntry(object):
    pass

class MonitorThread(object):
    def __init__(self, frequency = 0.5, do_suspend = True):
        self.entries = dict()
        self.keeprunning = True
        self.frequency = frequency
        self.do_suspend = do_suspend

    def safe_psutil_measure(self, fptr):
        try:
            return fptr()
        except psutil.AccessDenied:
            return None

    def run(self, pid, uuid):
        # Normally this wouldn't be safe, but the GIL fixes it for us ...
        process = psutil.Process(pid)
        self.entries['cmd'] = " ".join(process.cmdline)
        self.entries['start'] = time.time()
        self.entries['trial_id'] = str(uuid)
        self.entries['data'] = []
        while self.keeprunning:
            try:
                curr = MonitorEntry()
                curr.memory =  self.safe_psutil_measure(psutil.virtual_memory)
                curr.swap = self.safe_psutil_measure(psutil.swap_memory)
                curr.cpu = self.safe_psutil_measure(psutil.cpu_times)
                curr.disk = self.safe_psutil_measure(psutil.disk_io_counters)
                curr.ts = time.time()
                # So we don't end up getting tearing across our results, put the process to sleep before
                # we gather current information.
                if self.do_suspend:
                    process.suspend()
                curr.pmem = self.safe_psutil_measure(process.get_ext_memory_info)
                if hasattr(process, 'get_io_counters'):
                    curr.pdisk = self.safe_psutil_measure(process.get_io_counters)
                curr.pcpu = self.safe_psutil_measure(process.get_cpu_times)
                curr.pthreads = self.safe_psutil_measure(process.get_threads)
                curr.ctx = self.safe_psutil_measure(process.get_num_ctx_switches)
                mmaps = self.safe_psutil_measure(process.get_memory_maps)
                for curr_map in mmaps:
                    if(curr_map.path == "[heap]"):
                        curr.heap_size = curr_map.rss
                    if(curr_map.path == "[stack]"):
                        curr.stack_size = curr_map.rss
                if self.do_suspend:
                    process.resume()
                self.entries['data'].append(curr)
                time.sleep(self.frequency)
            except psutil.NoSuchProcess:
                self.keeprunning = False

class BenchmarkTrial(object):
    def __init__(self, basedir, template, bro, capture, realtime=False, bare=False, scripts=[]):
        self.basedir = basedir
        self.template = template
        self.dirstack = []
        self.bro = bro
        self.capture = capture
        self.realtime = realtime
        self.bare = bare
        self.scripts = scripts
        self.results = None
        self.uuid = None
        self.name = None

    def pushd(self, dirname):
        self.dirstack.append(os.getcwd())
        os.chdir(dirname)
        return self.dirstack

    def popd(self):
        if len(self.dirstack) > 0:
            os.chdir(self.dirstack.pop())
        return self.dirstack

    def json(self):
        return json.dumps(self.results, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def execute(self, name, params):
        self.uuid = uuid.uuid4()
        self.params = params
        # print "Opening template " + os.path.join(os.getcwd(), os.path.join('templates', self.template))
        run_script = Template(filename=os.path.join('templates', self.template))

        if not os.path.exists(self.basedir):
            os.makedirs(self.basedir)

        self.pushd(self.basedir)
        if(os.path.exists(name)):
            # print "Removing existing output directory: " + os.path.join(os.getcwd(), name)
            sh.rm('-fr', name)
        os.mkdir(name)
        # Render execution script template ...
        self.pushd(name)
        out_script = run_script.render(**self.params)
        # print "Launching trial in directory: " + os.getcwd()
        out_file = open(self.template, 'w')
        # ... to a file in our current directory.
        out_file.write(out_script)
        out_file.close()

        # Construct the bro argument string.
        args = []
        if(self.realtime):
            args.append('--pseudo-realtime')

        if(self.bare):
            args.append('-b')

        args.append('-r')
        args.append(self.capture)

        map(lambda x: args.append(x), self.scripts)

        monitor = MonitorThread()
        # print "Launching bro ... "
        process = self.bro(args, _bg=True)
        monitor_thread = threading.Thread(target = monitor.run, args = (process.pid, str(self.uuid), ))
        monitor_thread.start()
        process.wait()
        monitor.keeprunning = False
        monitor_thread.join()
        self.results = monitor.entries

        sh.rm('-f', sh.glob('*.log'))

        self.popd()
        self.popd()

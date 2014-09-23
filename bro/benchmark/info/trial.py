__author__ = 'clarkg1'

import json
import os
import sh
import shutil
import sys
import threading
import time
import uuid

# TODO: Violating DRY because I'm too lazy to think about how to do this better ... :/

class OptionsEnabled:
    PSUTIL_ENABLED = False
    MAKO_ENABLED = False

def import_error(item):
    print "Warning: unable to import `" + str(item) + "`"
    print "This is a fatal error, and this script will therefore terminate"
    print ""
    print "If using this script in conjunction with configure.py:"
    print "Please ensure that configure.py has been run *AND* that PYTHONPATH has been set to include the following:"
    print "* /path/to/pybrig/env/lib/python2.7/site-packages"
    print "* /path/to/pybrig/env/lib64/python2.7/site-packages"
    print ""
    print "For example:"
    print "export PYTHONPATH=/tmp/pybrig/env/lib/python2.7/site-packages:/tmp/pybrig/env/lib64/python2.7/site-packages"
    print ""
    print "Additionally, please be sure that LD_LIBRARY_PATH is set (e.g. to '/tmp/pybrig/env/lib') or that configure.py"
    print "was told to install packages into a known location (e.g. a directory listed in ld.so.conf)"
    sys.exit(-1)

try:
    import psutil
    OptionsEnabled.PSUTIL_ENABLED = True
except ImportError:
    import_error("psutil")
try:
    from mako.template import Template
    OptionsEnabled.MAKO_ENABLED = True
except ImportError:
    import_error("mako")

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

    def execute(self, name, params, callback=None):
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
        self.pushd(name)

        # Render execution script template ...
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

        # print "Launching bro ... "
        process = self.bro(args, _bg=True)
        process.wait()

        std_out = open('.stdout', 'w')
        std_out.write(process.stdout)
        std_out.close()
        
        std_err = open('.stderr', 'w')
        std_err.write(process.stderr)
        std_err.close()

        if callback:
            callback(self)

        sh.rm('-f', sh.glob('*.log'))

        self.popd()
        self.popd()


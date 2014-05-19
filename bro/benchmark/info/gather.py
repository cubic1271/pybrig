from ConfigParser import ConfigParser
import sh
from ctypes import CDLL
from ctypes import c_char_p
import ctypes.util as ctutil
import json
import os
import re
import uuid

class OptionsEnabled:
    SIGAR_ENABLED = False
    PSUTIL_ENABLED = False

try:
    import sigar
    OptionsEnabled.SIGAR_ENABLED = True
    import psutil
    OptionsEnabled.PSUTIL_ENABLED = True
except ImportError:
    print "Warning: unable to import sigar and / or psutil"
    print "Gather will continue, but some information may not be available"
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

class ExcludeInfoMatcher(object):
    def __init__(self):
        self.parser = ConfigParser()
        # No option conversion, since we're using the key as a regex here
        self.parser.optionxform = str
        cpath = os.path.realpath(__file__)
        self.parser.read([os.path.join(os.path.dirname(cpath), 'privacy.conf'), './privacy.conf'])

    def match(self, key, value, module, verbose=False):
        match_include = False
        match_exclude = False

        if len(self.parser.items(module + ".include")) == 0 and verbose:
            print "WARN: Matching against empty list of includes (for: " + module + ")"
        for item in self.parser.items(module + ".include"):
            if re.match(item[0], key) and re.match(item[1], value):
                match_include = True

        if len(self.parser.items(module + ".exclude")) == 0 and verbose:
            print "WARN: Matching against empty list of excludes (for: " + module + ")"
        for item in self.parser.items(module + ".exclude"):
            if re.match(item[0], key) and re.match(item[1], value):
                match_exclude = True

        return (not match_exclude) and (match_include)

class InterfaceInformation(object):
    def __init__(self, iface):
        self.name = iface.name()
        self.hwaddr = iface.hwaddr()
        self.address = iface.address()
        self.address6 = iface.address6()
        self.netmask = iface.netmask()

class CpuInformation(object):
    def __init__(self, cpu):
        self.cache = cpu.cache_size()
        self.cores_per_socket = cpu.cores_per_socket()
        self.mhz = cpu.mhz()
        self.model = cpu.model()
        self.total_cores = cpu.total_cores()
        self.total_sockets = cpu.total_sockets()
        self.vendor = cpu.vendor()

    def __str__(self):
        return "%s %s (%s MHz)" % (self.vendor, self.model, self.mhz)

    def __repr__(self):
        return "%s %s (%s MHz)" % (self.vendor, self.model, self.mhz)

class SystemInformation(object):
    def __init__(self):
        self.sysctl = dict()
        self.modules = []
        self.pcap_version = "(n/a)"
        self.cpus = []
        self.interfaces = []
        self.memory = 0L

    def gather(self):
        self.gather_sysctl()
        self.gather_modules()
        self.gather_pcap()
        self.gather_info()
        self.gather_facter()

    def gather_facter(self):
        matcher = ExcludeInfoMatcher()
        try:
            facter = sh.facter.bake(_cwd='.')
            self.facter = dict()
        except sh.CommandNotFound:
            return
        last = ""
        for line in facter(_iter=True):
            if " => " in line:
                res = line.split(" => ")
                self.facter[res[0].strip()] = res[1].strip()
                last = res[0]
            elif last != "":
                self.facter[last] += res[1].strip()

        # Post-process: filter gathered data based on rules defined in gather.conf
        for entry in self.facter.keys():
            if not matcher.match(entry, self.facter[entry], 'facter'):
                del self.facter[entry]

    def gather_sysctl(self):
        matcher = ExcludeInfoMatcher()
        self.sysctl = dict()
        sysctl = sh.sysctl.bake(_cwd='.')
        last = ""
        os_name = sh.uname().strip()
        for line in sysctl('-a', _iter=True):
            if os_name == "Linux":
                if " = " in line:
                    res = line.split(" = ")
                    self.sysctl[res[0].strip()] = res[1].strip()
                    last = res[0]
                elif last != "":
                    self.sysctl[last] += res[1].strip()
            elif os_name == "Darwin":
                if " = " in line:
                    res = line.split(" = ")
                    self.sysctl[res[0].strip()] = res[1].strip()
                    last = res[0].strip()
                elif ": " in line:
                    res = line.split(": ")
                    self.sysctl[res[0].strip()] = res[1].strip()
                    last = res[0].strip()
                elif last != "":
                    self.sysctl[last] += res[1].strip()

        # Post-process: filter gathered data based on rules defined in gather.conf
        for entry in self.sysctl.keys():
            if not matcher.match(entry, self.sysctl[entry], 'sysctl'):
                del self.sysctl[entry]

    def gather_modules(self):
        matcher = ExcludeInfoMatcher()
        if(sh.uname().strip() != "Linux"):
            return
        self.modules = []
        lsmod = sh.Command('/sbin/lsmod')
        skipped = False
        for line in lsmod(_iter=True):
            if not skipped:
                skipped = True
                continue
            self.modules.append(line.split(' ')[0])

        # Post-process: filter gathered data based on rules defined in gather.conf
        for entry in self.sysctl.keys():
            if not matcher.match(entry, self.modules[entry], 'modules'):
                del self.modules[entry]

    def gather_pcap(self):
        pcap_location = ctutil.find_library('pcap')
        if(pcap_location):
            pcap = CDLL(ctutil.find_library('pcap'))
            pcap.pcap_lib_version.restype = c_char_p
            self.pcap_version = pcap.pcap_lib_version()
        else:
            self.pcap_version = "(none)"

    def gather_info(self):
        matcher = ExcludeInfoMatcher()
        if OptionsEnabled.SIGAR_ENABLED:
            self.cpus = []
            info = sigar.open()
            list = info.cpu_info_list()
            for val in list:
                self.cpus.append(CpuInformation(val))
            list = info.net_interface_list()
            for val in list:
                curr = info.net_interface_config(val)
                tmp = InterfaceInformation(curr)
                for each in ['address', 'address6', 'hwaddr', 'netmask', 'name']:
                    if not matcher.match(each, getattr(tmp, each), 'interfaces'):
                        delattr(tmp, each)
                self.interfaces.append(tmp)
            info.close()
        if OptionsEnabled.PSUTIL_ENABLED:
            self.memory = psutil.TOTAL_PHYMEM
            self.partitions = psutil.disk_partitions()
        self.uuid = str(uuid.uuid1())

    def json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

import sigar
import sh
from ctypes import CDLL
from ctypes import c_char_p
import ctypes.util as ctutil
import psutil
import uuid
import json

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

    def gather_sysctl(self):
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

    def gather_modules(self):
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

    def gather_pcap(self):
        pcap_location = ctutil.find_library('pcap')
        if(pcap_location):
            pcap = CDLL(ctutil.find_library('pcap'))
            pcap.pcap_lib_version.restype = c_char_p
            self.pcap_version = pcap.pcap_lib_version()
        else:
            self.pcap_version = "(none)"

    def gather_info(self):
        self.cpus = []
        info = sigar.open()
        list = info.cpu_info_list()
        for val in list:
            self.cpus.append(CpuInformation(val))
        list = info.net_interface_list()
        for val in list:
            curr = info.net_interface_config(val)
            self.interfaces.append(InterfaceInformation(curr))
        info.close()
        self.memory = psutil.TOTAL_PHYMEM
        self.partitions = psutil.disk_partitions()
        self.uuid = str(uuid.uuid1())

    def json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

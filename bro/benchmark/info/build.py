__author__ = 'clarkg1'

import os
import sh
import sys
import urllib2
import platform

from os.path import basename
from urlparse import urlsplit

from optparse import OptionParser

class BuildConfiguration(object):
    def __init__(self, url, dirname):
        self.branch = None
        self.url = url
        self.dirname = dirname
        self.prefix = None
        self.autoconf = False
        self.dirstack = []
        self.do_retrieve = True
        self.do_build = True
        self.jobs = 1
        self.buildpath = '.'

    def pybuild(self):
        if not self.do_build:
            return
        self.pushd(os.path.join(self.dirname, self.buildpath))
        tmpenv = os.environ.copy()
        target = '.'.join(platform.python_version().split('.')[0:2])
        # OS X workaround: prevent error on unrecognized arguments.
        if "Darwin" in sh.uname('-a'):
            tmpenv['CPPFLAGS'] = '-Qunused-arguments'
            tmpenv['CFLAGS'] = '-Qunused-arguments'
        # Set appropriate python path.
        tmpenv['PYTHONPATH'] = self.prefix + '/lib/python' + target + '/site-packages:' + \
                               self.prefix + '/lib64/python' + target + '/site-packages'
        try:
            sh.python("setup.py", "install", "--prefix=" + self.prefix, _env=tmpenv)
        except sh.ErrorReturnCode,ex:
            print "Unable to build: %s" % ex.stderr
            raise ex
        self.popd()

    def build(self):
        if not self.do_build:
            return
        if(self.autoconf):
            sh.autoreconf("--force", "--install")
        configure = sh.Command("./configure")
        make = sh.make.bake(_cwd='./')
        if(self.prefix):
            configure('--prefix='+self.prefix)
        else:
            configure()
        make(j=self.jobs)

    def install(self):
        if not self.do_build:
            return
        sh.make.install()

    def clean(self):
        if not self.do_build:
            return
        sh.make.clean()

    def autobuild(self):
        self.retrieve()
        if not self.do_build:
            return
        self.pushd(os.path.join(self.dirname, self.buildpath))
        self.build()
        self.install()
        self.popd()

    def pushd(self, dirname):
        self.dirstack.append(os.getcwd())
        os.chdir(dirname)
        return self.dirstack

    def popd(self):
        if len(self.dirstack) > 0:
            os.chdir(self.dirstack.pop())
        return self.dirstack

    def cwd(self):
        return self.dirstack[len(self.dirstack) - 1]

    def retrieve(self):
        pass

class FileBuildConfiguration(BuildConfiguration):
    # http://stackoverflow.com/questions/862173/how-to-download-a-file-using-python-in-a-smarter-way
    @staticmethod
    def url2name(url):
        return basename(urlsplit(url)[2])

    @staticmethod
    def download(url, localFileName = None):
        localName = FileBuildConfiguration.url2name(url)
        req = urllib2.Request(url)
        r = urllib2.urlopen(req)
        if r.info().has_key('Content-Disposition'):
            localName = r.info()['Content-Disposition'].split('filename=')[1]
            if localName[0] == '"' or localName[0] == "'":
                localName = localName[1:-1]
        elif r.url != url:
            localName = FileBuildConfiguration.url2name(r.url)
        if localFileName:
            localName = localFileName
        f = open(localName, 'wb')
        f.write(r.read())
        f.close()
        return localName

    def retrieve(self):
        if self.do_retrieve:
            sh.rm("-fr", self.dirname)
            os.mkdir(self.dirname)
            self.pushd(self.dirname)
            retrieved = FileBuildConfiguration.download(self.url)
            if ".tar.gz" in retrieved:
                sh.tar("xvzf", retrieved)
            if ".tar.bz2" in retrieved:
                sh.tar("xjvf", retrieved)
            if ".zip" in retrieved:
                sh.unzip(retrieved)
        else:
            self.pushd(self.dirname)
        # Either one directory *OR* one directory + a README.
        if(len(os.listdir(".")) <= 3):
            # we can assume that we need to chdir before we can build, so set that to the local build path
            for curr in os.listdir("."):
                if(os.path.isdir(curr)):
                    self.buildpath = curr
        if not getattr(self, 'buildpath'):
            self.buildpath = "."
        self.popd()

class GitBuildConfiguration(BuildConfiguration):
    def retrieve(self):
        if self.do_retrieve:
            sh.rm("-fr", self.dirname)
            git = sh.git.bake(_cwd='./')
            git.clone('--recursive', self.url, self.dirname)
            self.pushd(self.dirname)
            if(self.branch):
                git.checkout(b=self.branch)
            self.popd()
            self.buildpath = "."

    def checkout(self, branch):
        git = sh.git.bake(_cwd='./')
        git.checkout(branch)

    def merge(self, branch):
        git = sh.git.bake(_cwd='./')
        git.merge(branch)

def build_sigar_python(target):
    target.pushd(os.path.join(target.dirname, target.buildpath))
    target.pushd('bindings')
    target.pushd('python')
    tmpenv = os.environ.copy()
    if "Darwin" in sh.uname('-a'):
        tmpenv['CPPFLAGS'] = '-Qunused-arguments'
        tmpenv['CFLAGS'] = '-Qunused-arguments'    

    try:    
        sh.python("setup.py", "--with-sigar="+target.prefix, "install", "--prefix="+target.prefix, _env=tmpenv)
    except sh.ErrorReturnCode,ex:
        print "Unable to build SIGAR python extensions: %s" % ex.stderr
        raise ex
    target.popd()
    target.popd()
    target.popd()

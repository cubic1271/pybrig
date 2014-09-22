__author__ = 'clarkg1'

from optparse import OptionParser
import os
import sh
import sys
import platform
import bro.benchmark.info.build as build

if __name__ == '__main__':
    install_dir = "/tmp/pybrig/env"
    src_dir = "/tmp/pybrig/src"

    parser = OptionParser()
    parser.add_option("-d", "--detailed-profile", action="store_true", dest="detailed", help="Pulls down a (highly experimental) branch that outputs additional profiling information when running bro", default=False)
    parser.add_option("-p", "--prefix", action="store", dest="prefix", help="Benchmark packages are installed into this directory path.", default=install_dir, metavar="INSTALL_DIR")
    parser.add_option("-s", "--srcdir", action="store", dest="srcdir", help="Benchmark packages are downloaded into and built in this directory path.", default=src_dir, metavar="SOURCE_DIR")
    parser.add_option("-R", "--no-retrieve", action="store_true", dest="no_retrieve", help="Do not try to retrieve dependencies.  Instead, only try to build them.", default=False)
    parser.add_option("-B", "--no-build", action="store_true", dest="no_build", help="Do not try to build dependencies.  Instead, only retrieve them.  Normally combined with '-P'.", default=False)
    parser.add_option("-S", "--source-package", action="store", dest="src_package", help="Extract sources from PACKAGE into SOURCE_DIR before installing.  Normally combined with '-R'.", metavar="PACKAGE", default=None)
    parser.add_option("-P", "--package", action="store", dest="do_package", help="Package dependencies and store in PACKAGE.  Format is determined by filename: .tar.gz and .tar.bz2 are supported.", metavar="PACKAGE", default=None)
    (options, args) = parser.parse_args()

    install_dir = options.prefix
    src_dir = options.srcdir

    print "Installation directory: " + install_dir
    print "Source directory: " + src_dir

    if not os.path.exists(src_dir):
        print "Creating source directory ..."
        os.makedirs(src_dir)

    if(options.src_package):
        if "http://" in options.src_package or "https://" in options.src_package:
            build.FileBuildConfiguration.download(options.src_package, '/tmp/' + options.src_package)
            options.src_package = '/tmp/' + options.src_package

        if not os.path.exists(options.src_package):
            raise OSError(options.src_package + " not found.")
        print "Extracting " + options.src_package + " into " + src_dir
        tmp = build.BuildConfiguration(None, None)
        tmp.pushd(src_dir)
        if ".tar.bz2" in options.src_package or ".tbz2" in options.src_package:
            sh.tar('xjf', options.src_package)
        if ".tar.gz" in options.src_package or ".tgz" in options.src_package:
            sh.tar('xzf', options.src_package)
        tmp.popd()

    #  A little bit of polish to make sure the directories containing our installed dependencies end up in our python path ...
    target = '.'.join(platform.python_version().split('.')[0:2])

    try:
        os.makedirs(install_dir + '/lib/python' + target + '/site-packages')
        os.makedirs(install_dir + '/lib64/python' + target + '/site-packages')
    except OSError:
        pass

    print "Starting run ..."

    print "Executing jobs for mako ..."
    mako = build.FileBuildConfiguration('https://pypi.python.org/packages/source/M/Mako/Mako-0.8.1.tar.gz', os.path.join(src_dir, 'mako'))
    mako.prefix = install_dir
    mako.do_build = not options.no_build
    mako.do_retrieve = not options.no_retrieve
    result = mako.retrieve()
    result = mako.pybuild()

    print "Executing jobs for psutil ..."
    psutil = build.FileBuildConfiguration('https://pypi.python.org/packages/source/p/psutil/psutil-2.0.0.tar.gz#md5=9ee83ff3d68396f91ebdf71ae83b152d', os.path.join(src_dir, 'psutil'))
    psutil.prefix = install_dir
    psutil.do_build = not options.no_build
    psutil.do_retrieve = not options.no_retrieve
    result = psutil.retrieve()
    result = psutil.pybuild()

    print "Executing jobs for SIGAR ..."
    sigar = build.GitBuildConfiguration('https://github.com/cubic1271/sigar', os.path.join(src_dir, 'sigar'))
    sigar.do_retrieve = not options.no_retrieve
    sigar.do_build = not options.no_build
    sigar.autoconf = True
    sigar.prefix = install_dir
    sigar.autobuild()
    if not options.no_build:
        print "Executing jobs for SIGAR bindings ..."
        build.build_sigar_python(sigar)

    print "Executing jobs for ipsumdump ..."
    ipsumdump = build.FileBuildConfiguration('http://www.read.seas.harvard.edu/~kohler/ipsumdump/ipsumdump-1.82.tar.gz', os.path.join(src_dir, 'ipsumdump'))
    ipsumdump.do_build = not options.no_build
    ipsumdump.do_retrieve = not options.no_retrieve
    ipsumdump.prefix = install_dir
    result = ipsumdump.autobuild()

    bro_env = os.environ.copy()
    bro_env['LDFLAGS'] = '-L' + os.path.join(os.path.join(os.path.join(src_dir, 'instrumentation'), 'aux'), 'syshook') + ' -lsyshook-malloc -lsyshook-io'
    bro_env['LD_LIBRARY_PATH'] = os.path.join(os.path.join(os.path.join(src_dir, 'instrumentation'), 'aux'), 'syshook')

    print "Executing preload jobs for bro-plugin-instrumentation ..."
    plugin_inst = build.GitBuildConfiguration('https://github.com/cubic1271/bro-plugin-instrumentation', os.path.join(src_dir, 'instrumentation'))
    plugin_inst.retrieve()
    plugin_inst.pushd(plugin_inst.dirname)
    plugin_inst.make(command='preload')
    plugin_inst.popd()

    print "Executing jobs for bro (vanilla, master) ..."
    bro = build.GitBuildConfiguration('https://github.com/bro/bro', os.path.join(src_dir, 'bro'), env=bro_env)

    bro.do_build = not options.no_build
    bro.do_retrieve = not options.no_retrieve
    # A little bit of custom work to do here, since we need to change branches in a submodule to pick up the
    # appropriate CMake entry to find PAPI ...
    if not options.no_retrieve:
        print "Fetching source ..."
    bro.retrieve()
    bro.pushd(bro.dirname)
    bro.checkout('topic/gilbert/plugin-api-tweak')
    bro.popd()

    bro.prefix = install_dir
    bro.jobs = 8

    bro.pushd(bro.dirname)

    if not options.no_build:
        print "Compiling ..."
        bro.build()
        print "Installing ..."
        bro.install()

    bro.popd()

    print "Executing jobs for bro-plugin-instrumentation ..."
    bro_env['BRO'] = os.path.join(src_dir, 'bro')
    plugin_inst = build.GitBuildConfiguration('https://github.com/cubic1271/bro-plugin-instrumentation', os.path.join(src_dir, 'instrumentation'), env=bro_env)
    plugin_inst.pushd(plugin_inst.dirname)
    plugin_inst.make()
    plugin_inst.install()
    plugin_inst.popd()

    if not options.no_build:
        print "There is now a usable installation configured at " + install_dir + ".  Go forth and benchmark."

    if options.do_package:
        print "Building source package: " + options.do_package
        bro.pushd(src_dir)
        if ".tar.gz" in options.do_package or ".tgz" in options.do_package:
            sh.tar('czf', options.do_package, sh.glob('*'))
        if ".tar.bz2" in options.do_package or ".tbz2" in options.do_package:
            sh.tar('cjf', options.do_package, sh.glob('*'))
        print "Done."


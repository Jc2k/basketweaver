"""
From Chris McDonough:

If it's not labeled otherwise and it comes from us, it's released under this license... http://repoze.org/license.html (BSD-like)...

"""

import os
import setuptools
import shutil
import subprocess
import sys
import tarfile
import zipfile
import tempfile

class TarArchive:
    def __init__(self, filename):
        self.filename = filename
	mode = "r"
	if filename.endswith('.bz2'):
	    mode = "r:bz2"
	elif filename.endswith('.gz') or filename.endswith('.tgz'):
	    mode = "r:gz"
        self.tgz = tarfile.TarFile.open(filename, mode)

    def names(self):
        return self.tgz.getnames()

    def lines(self, name):
        return self.tgz.extractfile(name).readlines()

    def extract(self, name, tempdir):
        return self.tgz.extract(name, tempdir)

    def extractall(self, tempdir):
        os.system('cd %s && tar xzf %s' % (tempdir, 
                                           os.path.abspath(self.filename)))

    def close(self):
        return self.tgz.close()
 
class ZipArchive:
    def __init__(self, filename):
        self.filename = filename
        self.zipf = zipfile.ZipFile(filename, 'r')

    def names(self):
        return self.zipf.namelist()

    def lines(self, name):
        return self.zipf.read(name).split('\n')

    def extract(self, name, tempdir):
        data = self.zipf.read(name)
        fn = name.split(os.sep)[-1]
        fn = os.path.join(tempdir, fn)
        f = open(fn, 'wb')
        f.write(data)

    def extractall(self, tempdir):
        os.system('cd %s && unzip %s' % (tempdir, 
                                         os.path.abspath(self.filename)))

    def close(self):
        return self.zipf.close()

def _extractNameVersion(filename, tempdir):
    print 'Parsing:', filename

    def _write_cache_file(filename, project, version):
        """ Write out a version cache file """
        cache_file = open(filename + '.version_cache', 'w')
        cache_file.write(project + '\n')
        cache_file.write(version)
        cache_file.close()

    def _read_cache_file(filename):
        """ Read out the cached version number """
        cache_file = open(filename + '.version_cache', 'r')
        project, version = cache_file.read().split('\n')
        return project, version
        

    if filename.endswith('.gz') or filename.endswith('.tgz') or filename.endswith('.bz2'):
        archive = TarArchive(filename)
    elif filename.endswith('.egg') or filename.endswith('.zip'):
        archive = ZipArchive(filename)
    else:
        return

    # try and get the cached version
    # if it exists, return those
    # if we get an exception, carry on and do some analysis
    try:
        project, version =_read_cache_file(filename)
        print "Using cache for: " + project + " " + version
        return project, version
    except:
        pass


    try:
        for name in archive.names():
            if len(name.split('/'))==2  and name.endswith('PKG-INFO'):

                project, version = None, None

                lines = archive.lines(name)
                for line in lines:
                    if not ":" in line:
                        continue
                    key, value = line.split(':', 1)

                    if key == 'Name':
                        print filename, value
                        project = value.strip()
                    elif key == 'Version':
                        version = value.strip()

                    if project is not None and version is not None:
                        _write_cache_file(filename, project, version)
                        return project, version
                continue;

        # no PKG-INFO found, do it the hard way.
        archive.extractall(tempdir)
        dirs = os.listdir(tempdir)
        dir = os.path.join(tempdir, dirs[0])
        if not os.path.isdir(dir):
            dir = tempdir
        command = ('cd %s && %s setup.py --name --version'
                   % (dir, sys.executable))
        popen = subprocess.Popen(command,
                                 stdout=subprocess.PIPE,
                                 shell=True,
                                 )
        output = popen.communicate()[0]
        return output.splitlines()[:2]
    finally:
        archive.close()


def _clean(filename):
    """ Clean any cache files """
    if filename.endswith('.version_cache'):
        print "Removing: " + filename
        os.remove(filename)

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if '--clean' in argv:
        print 'Clean activated'
        for arg in argv:
            _clean(arg)
        return

    name_map = {}

    projects = {}
    for arg in argv:
        if arg.startswith('*'):
            continue
        # ignore version cache files
        if arg.endswith('.version_cache'):
            continue
        try:
            try:
                tempdir = tempfile.mkdtemp()
                project, revision = _extractNameVersion(arg, tempdir)

                # Make a map of all the projects, but and group different flavours
                # of the same name
                foo = name_map.setdefault(project.lower(), [])
                if not project in foo:
                    foo.append(project)

                projects.setdefault(project.lower(), []).append((revision, arg))
            except:
                print "Couldn't find version info"
        finally:
            shutil.rmtree(tempdir)

    inverse_name_map = {}
    for k, v in name_map.iteritems():
        for variant in v:
            inverse_name_map[variant] = projects[k]

    items = inverse_name_map.items()
    items.sort()
    topname = 'index'

    if not os.path.exists(topname):
        os.makedirs(topname)
    top = open('%s/index.html' % topname, 'w')
    top.writelines(['<html>\n',
                    '<body>\n',
                    '<h1>Package Index</h1>\n',
                    '<ul>\n'])

    for key, value in items:
        print 'Project: %s' % key
        dirname = '%s/%s' % (topname, key)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        top.write('<li><a href="%s/index.html">%s</a>\n' % (key, key))

        sub = open('%s/%s/index.html' % (topname, key), 'w')
        sub.writelines(['<html>\n',
                        '<body>\n',
                        '<h1>%s Distributions</h1>\n' % key,
                        '<ul>\n'])

        for revision, archive in value:
            print '  -> %s, %s' % (revision, archive)
            sub.write('<li><a href="../../%s">%s</a>\n' % (archive, archive))

        sub.writelines(['</ul>\n',
                        '</body>\n',
                        '</html>\n'])

    top.writelines(['</ul>\n',
                    '</body>\n',
                    '</html>\n'])
    top.close()

if __name__ == '__main__':
    main()

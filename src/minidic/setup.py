
import glob
import os
import py2exe
import sys

from distutils.core import setup


# Default to running py2exe
if len(sys.argv) == 1:
    sys.argv.append('py2exe')


opj = os.path.join

RT_MANIFEST = 24

def walkFiles(path):
    for root, dirs, files in os.walk(path):
        if '.svn' in (x.lower() for x in dirs):
            dirs.remove('.svn')
        if '.git' in (x.lower() for x in dirs):
            dirs.remove('.git')
        for file in files:
            yield opj(root, file)


setup(
    console = [
        {
            'script': 'compile.py',
            'description': 'MiniDIC',
            'dest_base': 'minidic',
        }
    ],
    zipfile = None,
    options = {
        'py2exe': {
            'compressed': 1,
            'optimize': 2,
            'bundle_files': 1,
            'dist_dir': opj('..','..','bin'),
        },
    },
)

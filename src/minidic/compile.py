
#
# MiniD Interface Compiler
#
# Usage: minidic PKG MDIFILE
#        minidic PKG package.mdi
#

__all__ = ['compile']

import codecs
import os.path

from ast import AstModule, AstPackage
from parse import LexStream, parseStart
from source import Source
from semantic import SemAstVisitor, SemState
from sit import SemPackage
from minidcg import CGSemVisitor, CGState
from writer import Writer
from walkers import walkImports


def drop_tail(path, n):
    while n > 0:
        path,_ = os.path.split(path)
        n = n - 1
    return path


def compile(pkg, path, follow=True, done=None):
    if done is None: done = set()
    if path in done: return

    print path
    done.add(path)

    astRoot = parseStart(LexStream(Source(path)))

    semst = SemState()
    semv = SemAstVisitor()
    semRoot = semv.visit(astRoot, semst)

    outpath = os.path.splitext(path)[0]+".d"
    outf = codecs.open(outpath, 'w', 'utf-8')
    o = Writer(outf)
    cgst = CGState(o)
    cgv = CGSemVisitor()
    cgv.targetPath = outpath
    cgv.package = pkg if pkg and pkg != "" else None
    cgv.visit(semRoot, cgst)

    if follow:
        base = drop_tail(
            path,
            len(semRoot.fqi.split('.'))
            + (1 if isinstance(semRoot, SemPackage) else 0))

        for imp in walkImports(semRoot):
            newPath = os.path.join(base, os.path.join(*imp.module.split('.')))
            modPath = None
            if os.path.isdir(newPath):
                modPath = os.path.join(newPath, '__package__.mdi')
            else:
                modPath = newPath + '.mdi'

            if not os.path.exists(modPath):
                print 'Warning: missing module %s' % modPath
                continue
                
            compile(pkg, modPath, done=done)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print 'Usage: compile.py (PKG|-) FILE'
        print '       (got: %r)' % sys.argv
        sys.exit(1)

    pkg = sys.argv[1]
    pkg = pkg if pkg != "-" else None
    
    compile(pkg, sys.argv[2])


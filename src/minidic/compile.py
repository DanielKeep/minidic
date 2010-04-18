
import codecs
import os.path

from parse import LexStream, parseStart
from source import Source
from semantic import SemAstVisitor, SemState
from minidcg import CGSemVisitor, CGState
from writer import Writer


def compile(path):
    moduleAst = parseStart(LexStream(Source(path)))

    semst = SemState()
    semv = SemAstVisitor()
    moduleSem = semv.visit(moduleAst, semst)

    outpath = os.path.splitext(path)[0]+".d"
    outf = codecs.open(outpath, 'w', 'utf-8')
    o = Writer(outf)
    cgst = CGState(o)
    cgv = CGSemVisitor()
    cgv.targetPath = outpath
    cgv.package = 'test.minid'
    cgv.visit(moduleSem, cgst)


compile('test.mdi')


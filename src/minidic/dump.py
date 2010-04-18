
from lexer import *
from parse import *
from semantic import *
from writer import *

src = Source('test.mdi')
ls = LexStream(src)
node = parseStart(ls)

node.dump(Writer())

st = SemState()
sv = SemAstVisitor()

sn = sv.visit(node, st)

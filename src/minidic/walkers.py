
from sit import *

def walkImports(node):
    return (d for d in node.decls if isinstance(d, SemImportDecl))


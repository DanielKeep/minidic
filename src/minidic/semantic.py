

from ast import *
from sit import *
from writer import Writer

from itertools import groupby


class SemState(object):

    enclosingType = None
    annots = None
    isOpArg = False

    isPackage = False

    def __init__(self):
        self.annots = []



class SemAstVisitor(AstVisitor):

    def __init__(self):
        super(SemAstVisitor, self).__init__()


    def visit(self, node, st):
        sn = super(SemAstVisitor,self).visit(node, st)
        if isinstance(sn, SemNode):
            if not sn.valid():
                import pdb;pdb.set_trace()
                assert False, "invalid %s generated" % str(type(sn))
        elif isinstance(sn, list):
            for e in sn:
                if not e.valid():
                    import pdb;pdb.set_trace()
                    assert False, "invalid %s generated" % str(type(e))
        else:
            import pdb;pdb.set_trace()
            assert False, "invalid %s generated" % str(type(e))

        return sn


    def defaultVisit(self, node, st):
        assert False, "unimplemented visit for %r" % node


    def visitAstModule(self, node, st):
        sn = SemModule()
        sn.src = node.src
        sn.fqi = node.fqi
        
        for decl in node.decls:
            if isinstance(decl, AstAnnotScope):
                sn.decls += self.visit(decl, st)
            else:
                sn.decls.append(self.visit(decl, st))

        return sn


    def visitAstPackage(self, node, st):
        sn = SemPackage()
        sn.src = node.src
        sn.fqi = node.fqi

        st.isPackage = node.fqi

        for decl in node.decls:
            if isinstance(decl, AstImportDecl):
                sn.decls.append(self.visit(decl, st))

            else:
                assert False, "unexpected %s in package" % str(type(decl))

        st.isPackage = False

        return sn


    def visitAstImportDecl(self, node, st):
        sn = SemImportDecl()
        sn.src = node.src
        sn.isPackage = node.isPackage
        sn.module = node.module
        sn.symbol = node.symbol

        if sn.symbol is None:
            sn.symbol = sn.module.rsplit('.', 1)[-1]

        if st.isPackage:
            sn.module = st.isPackage + '.' + sn.module

        return sn


    def visitAstConstDecl(self, node, st):
        sn = SemConstDecl()
        sn.src = node.src
        sn.ident = node.ident
        sn.type = self.visit(node.type, st)

        return sn


    def visitAstClassDecl(self, node, st):
        sn = SemClassDecl()
        sn.src = node.src
        sn.ident = node.ident

        for annot in (a.ident for a in (node.annots or []) + st.annots):
            if annot == "final":
                sn.isFinal = True

            elif annot == "nativeLocal":
                sn.nativeLocal = True

            else:
                assert False, "unknown class annotation '%s'" % annot

        oldET = st.enclosingType
        st.enclosingType = sn

        oldAn = st.annots
        st.annots = []

        funcDecls = []

        def addDecl(decl):
            if isinstance(decl, SemFuncDecl) and decl.ident == "this":
                sn.ctors.append(decl)
            elif isinstance(decl, SemFuncDecl) or isinstance(decl, SemOpDecl):
                funcDecls.append(decl)
            else:
                sn.decls.append(decl)
        
        for decl in node.decls:
            if isinstance(decl, AstAnnotScope):
                for subdecl in self.visit(decl, st):
                    addDecl(subdecl)
            else:
                addDecl(self.visit(decl, st))

        for (fnIdent, overloads) in groupby(funcDecls, lambda d: d.ident):
            overloads = list(overloads)
            if len(overloads) == 1:
                sn.decls.append(overloads[0])

            else:
                ov = SemOverloadDecl()
                ov.ident = fnIdent
                ov.type = type(overloads[0])
                ov.overloads = sorted(overloads,
                                      key=lambda o: len(o.args),
                                      reverse=True)
                assert ov.valid()
                sn.decls.append(ov)

        st.annots = oldAn
        st.enclosingType = oldET

        return sn


    def visitAstStructDecl(self, node, st):
        sn = SemStructDecl()
        sn.src = node.src
        sn.ident = node.ident

        for annot in (a.ident for a in (node.annots or []) + st.annots):
            if annot == "nativeLocal":
                sn.nativeLocal = True

            else:
                assert False, "unknown struct annotation '%s'" % annot

        oldET = st.enclosingType
        st.enclosingType = sn

        oldAn = st.annots
        st.annots = []

        decls = []
        funcDecls = []

        def addDecl(decl):
            if isinstance(decl, SemFuncDecl) and decl.ident == "this":
                sn.ctors.append(decl)
            elif isinstance(decl, SemFuncDecl) or isinstance(decl, SemOpDecl):
                funcDecls.append(decl)
            else:
                sn.decls.append(decl)
        
        for decl in node.decls:
            if isinstance(decl, AstAnnotScope):
                for subdecl in self.visit(decl, st):
                    addDecl(subdecl)
            else:
                addDecl(self.visit(decl, st))

        for (fnIdent, overloads) in groupby(funcDecls, lambda d: d.ident):
            overloads = list(overloads)
            if len(overloads) == 1:
                sn.decls.append(overloads[0])

            else:
                ov = SemOverloadDecl()
                ov.ident = fnIdent
                ov.type = type(overloads[0])
                ov.overloads = sorted(overloads,
                                      key=lambda o: len(o.args),
                                      reverse=True)
                assert ov.valid()
                sn.decls.append(ov)

        st.annots = oldAn
        st.enclosingType = oldET

        return sn


    def visitAstRoDecl(self, node, st):
        sn = SemRoDecl()
        sn.src = node.src
        sn.ident = node.ident
        sn.type = self.visit(node.type, st)

        return sn


    def visitAstRwDecl(self, node, st):
        sn = SemRwDecl()
        sn.src = node.src
        sn.ident = node.ident
        sn.type = self.visit(node.type, st)

        return sn


    def visitAstFuncDecl(self, node, st):
        sn = SemFuncDecl()
        sn.src = node.src
        sn.ident = node.ident

        if node.ident == "this":
            assert node.returnType is None, "constructors cannot have a return type"
        
        if node.returnType is not None:
            sn.returnType = self.visit(node.returnType, st)
        else:
            sn.returnType = SemSymbolType()
            sn.returnType.ident = "void"

        for annot in (a.ident for a in (node.annots or []) + st.annots):
            if annot == "final":
                sn.isFinal = True

            elif annot == "static":
                sn.isStatic = True

            else:
                assert False, "unknown func annotation '%s'" % annot

        for arg in node.args:
            sn.args.append(self.visit(arg, st))

        if node.body is not None:
            sn.body = self.visit(node.body, st)

        return sn


    def visitAstOpDecl(self, node, st):
        sn = SemOpDecl()
        sn.src = node.src
        sn.ident = node.ident

        # sn.args defaults to an empty list; clear it
        sn.args = None

        if node.returnType is not None:
            sn.returnType = self.visit(node.returnType, st)

        if node.args is not None:
            st.isOpArg = True
            sn.args = [self.visit(arg, st) for arg in node.args]
            st.isOpArg = False

        if sn.args is None:
            sn.args = guessOpArgs(sn.ident, st)

            if sn.args is None:
                # Urgh, I give up!
                sn.args = []

        if sn.returnType is None:
            sn.returnType = guessOpReturnType(sn.ident, st)

        if node.body is not None:
            sn.body = self.visit(node.body, st)

        return sn


    def visitAstAnnotScope(self, node, st):
        sns = []

        oldAn = st.annots
        st.annots = node.annots

        for decl in node.decls:
            if isinstance(decl, AstAnnotScope):
                sns += self.visit(decl, st)
            else:
                sns.append(self.visit(decl, st))

        st.annots = oldAn

        return sns


    def visitAstArgument(self, node, st):
        sn = SemArgument()
        sn.src = node.src
        sn.ident = node.ident
        sn.isOpArg = st.isOpArg

        for annot in (a.ident for a in (node.annots or [])):
            if annot == 'ref':
                sn.isRef = True

            elif annot == 'out':
                sn.isOut = True

            elif annot == 'lazy':
                sn.isLazy = True

            elif annot == 'vararg':
                sn.isVararg = True

            else:
                assert False, "unknown arg annotation '%s'" % annot

        st.isOpArg = False
        sn.type = self.visit(node.type, st)
        st.isOpArg = sn.isOpArg

        return sn


    def visitAstSymbolType(self, node, st):
        sn = SemSymbolType()
        sn.src = node.src
        sn.ident = node.ident
        
        return sn


    def visitAstArrayType(self, node, st):
        sn = SemArrayType()
        sn.src = node.src
        sn.elemType = self.visit(node.elemType, st)
        
        return sn


    def visitAstMixin(self, node, st):
        sn = SemMixin()
        sn.src = node.src
        sn.code = node.code
        
        return sn



UNARY_OPS = (
    'neg', 'pos', 'com', 'postInc', 'postDec',
)

CLOSED_BINARY_OPS = (
    'add', 'sub', 'mul', 'div', 'mod', 'and',
    'or', 'xor', 'shl', 'shr', 'ushr', 'cat',
    'add_r', 'sub_r', 'mul_r', 'div_r', 'mod_r', 'and_r',
    'or_r', 'xor_r', 'shl_r', 'shr_r', 'ushr_r', 'cat_r',
    'addAssign', 'subAssign', 'mulAssign', 'divAssign',
    'modAssign', 'andAssign', 'orAssign', 'xorAssign',
    'shlAssign', 'shrAssign', 'ushrAssign', 'catAssign',
)

SELF_BINARY_OPS = (
    'equals',
    'cmp',
)

def guessOpArgs(name, st):
    if name in UNARY_OPS:
        return []

    if name in CLOSED_BINARY_OPS:
        ty = SemSymbolType()
        ty.ident = st.enclosingType.ident

        arg = SemArgument()
        arg.type = ty
        arg.isOpArg = True
        
        return [arg]

    if name in SELF_BINARY_OPS:
        et = st.enclosingType
        ty = SemSymbolType()
        
        if isinstance(et, SemClassDecl):
            ty.ident = "Object"
        elif isinstance(et, SemStructDecl):
            ty.ident = et.ident
        else:
            assert False

        arg = SemArgument()
        arg.type = ty
        arg.isOpArg = True

        return [arg]
    
    assert False, "could not determine arguments for operator '%s'" % name


CLOSED_RT_OPS = (
    'neg', 'pos', 'com', 'postInc', 'postDec',
    'add', 'sub', 'mul', 'div', 'mod', 'and',
    'or', 'xor', 'shl', 'shr', 'uShr', 'cat',
    'add_r', 'sub_r', 'mul_r', 'div_r', 'mod_r', 'and_r',
    'or_r', 'xor_r', 'shl_r', 'shr_r', 'uShr_r', 'cat_r',
)

VOID_RT_OPS = (
    'assign',
    'addAssign', 'subAssign', 'mulAssign', 'divAssign',
    'modAssign', 'andAssign', 'orAssign', 'xorAssign',
    'shlAssign', 'shrAssign', 'ushrAssign', 'catAssign',
)

OP_RETURN_TYPES = {
    'equals': 'int',
    'cmp': 'int',
    'in': 'bool',
    #'in_r': 'bool',
}


def guessOpReturnType(name, st):
    if name in CLOSED_RT_OPS:
        assert st.enclosingType is not None
        ty = SemSymbolType()
        ty.ident = st.enclosingType.ident
        return ty

    if name in VOID_RT_OPS:
        ty = SemSymbolType()
        ty.ident = "void"
        return ty

    if name in OP_RETURN_TYPES:
        ty = SemSymbolType()
        ty.ident = OP_RETURN_TYPES[name]
        return ty

    assert False, "could not determine return type of operator '%s'" % name



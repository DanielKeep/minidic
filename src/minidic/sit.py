

class SemVisitor(object):

    def __init__(self):
        pass


    def visit(self, node, st):
        name = "visit" + type(node).__name__
        if hasattr(self, name):
            return getattr(self, name)(node, st)
        else:
            return self.defaultVisit(node, st)


    def defaultVisit(self, node, st):
        pass


    
class SemNode(object):

    src = None

    def valid(self):
        return False



class SemModule(SemNode):

    fqi = None
    decls = None

    def __init__(self):
        self.decls = []


    def valid(self):
        return all((
            self.fqi is not None and self.fqi != "",
            self.decls is not None,
            all(isinstance(decl, SemDecl) for decl in self.decls),
        ))



class SemDecl(SemNode):
    pass



class SemImportDecl(SemDecl):

    module = None
    symbol = None

    def valid(self):
        return all((
            self.module is not None,
            self.symbol is not None,
        ))



class SemConstDecl(SemDecl):

    ident = None
    type = None

    def valid(self):
        return all((
            self.ident is not None,
            isinstance(self.type, SemType),
        ))



class SemAggregateDecl(SemDecl):

    ident = None
    ctors = None
    decls = None

    nativeLocal = False

    def __init__(self):
        self.ctors = []
        self.decls = []

    def valid(self):
        return all((
            self.ident is not None,
            self.ctors is not None,
            all(isinstance(decl, SemFuncDecl) for decl in self.ctors),
            all(decl.ident == "this" for decl in self.ctors),
            self.decls is not None,
            all(isinstance(decl, SemDecl) for decl in self.decls),
            all(decl.ident != "this" for decl in self.decls
                if isinstance(decl, SemFuncDecl)),
        ))



class SemClassDecl(SemAggregateDecl):

    isFinal = False



class SemStructDecl(SemAggregateDecl):
    pass



class SemAccessorDecl(SemDecl):

    ident = None
    type = None

    def valid(self):
        return all((
            self.ident is not None,
            isinstance(self.type, SemType),
        ))



class SemRoDecl(SemAccessorDecl):
    pass



class SemRwDecl(SemAccessorDecl):
    pass



class SemFuncDecl(SemDecl):

    ident = None
    args = None
    returnType = None
    body = None

    isFinal = False
    isStatic = False

    def __init__(self):
        self.args = []

    def valid(self):
        return all((
            self.ident is not None,
            self.args is not None,
            all(isinstance(arg, SemArgument) for arg in self.args),
            isinstance(self.returnType, SemType),
            isinstance(self.body, SemMixin) if self.body is not None else True,
        ))



class SemOpDecl(SemDecl):

    ident = None
    args = None
    returnType = None
    body = None

    def __init__(self):
        self.args = []

    def valid(self):
        return all((
            self.ident is not None,
            self.args is not None,
            all(isinstance(arg, SemArgument) for arg in self.args),
            isinstance(self.returnType, SemType),
            isinstance(self.body, SemMixin) if self.body is not None else True,
        ))



class SemOverloadDecl(SemDecl):

    ident = None
    type = None
    overloads = None

    def __init__(self):
        self.overloads = []

    def valid(self):
        return all((
            self.ident is not None,
            issubclass(self.type, SemDecl),
            all(isinstance(ol, self.type) for ol in self.overloads),
            all(ol.ident == self.ident for ol in self.overloads),
        ))



class SemArgument(SemNode):

    ident = None
    type = None

    isOpArg = False

    isRef = False
    isOut = False
    isLazy = False
    isVararg = False

    def valid(self):
        return all((
            self.isOpArg or self.ident is not None,
            isinstance(self.type, SemType),
        ))



class SemType(SemNode):
    pass



class SemSymbolType(SemType):

    ident = None

    def valid(self):
        return all((
            self.ident is not None,
        ))



class SemArrayType(SemType):

    elemType = None

    def valid(self):
        return all((
            isinstance(self.elemType, SemType),
        ))



class SemMixin(SemDecl):

    code = None

    def valid(self):
        return all((
            self.code is not None,
        ))



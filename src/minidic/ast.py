

class AstVisitor(object):

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
        


class AstNode(object):

    src = None

    def dump(self, o):
        o.fl("AstNode (%r)", self)


    def copyAs(self, type):
        r = type()
        r.src = self.src
        return r



class AstModule(AstNode):

    fqi = None
    decls = None

    def __init__(self):
        self.decls = []


    def dump(self, o):
        o.fl("Module %s", self.fqi)
        o.push("{")
        for decl in self.decls:
            decl.dump(o)
        o.pop("}")



class AstPackage(AstNode):

    fqi = None
    decls = None

    def __init__(self):
        self.decls = []


    def dump(self, o):
        o.fl("Package %s", self.fqi)
        o.push("{")
        for decl in self.decls:
            decl.dump(o)
        o.pop("}")



class AstDecl(AstNode):
    pass



class AstImportDecl(AstDecl):

    module = None
    symbol = None

    def dump(self, o):
        o.fl("Import %s%s", self.module,
             " : %s" % self.symbol if self.symbol is not None
             else "")



class AstConstDecl(AstDecl):

    ident = None
    type = None
    
    def dump(self, o):
        o.f("Const %s : ", self.ident)
        if self.type:
            self.type.dump(o)
            o.l()
        else:
            o.pl("void")



class AstAggregateDecl(AstDecl):

    ident = None
    annots = None
    decls = None

    def __init__(self):
        self.annots = []
        self.decls = []


    def copyAs(self, type):
        r = super(AstAggregateDecl,self).copyAs(type)
        r.ident = self.ident
        r.annots = self.annots
        r.decls = self.decls
        return r


    def dumpAgg(self, type, o):
        o.fl("%s %s", type, self.ident)
        o.push("{")

        if self.annots:
            for annot in self.annots:
                o.p("Annot ")
                annot.dump(o)
                o.l()
                
        o.push("{")
        
        for decl in self.decls:
            decl.dump(o)
            
        o.pop("}")
        o.pop("}")



class AstClassDecl(AstAggregateDecl):

    def dump(self, o):
        self.dumpAgg("Class", o)



class AstStructDecl(AstAggregateDecl):

    def dump(self, o):
        self.dumpAgg("Struct", o)



class AstAccessorDecl(AstDecl):

    ident = None
    type = None

    def copyAs(self, type):
        r = super(AstAccessorDecl,self).copyAs(type)
        r.ident = self.ident
        r.type = self.type
        return r


    def dumpAcc(self, type, o):
        o.f("%s %s : ", type, self.ident)
        self.type.dump(o)
        o.l()



class AstRoDecl(AstAccessorDecl):

    def dump(self, o):
        self.dumpAcc("Ro", o)



class AstRwDecl(AstAccessorDecl):

    def dump(self, o):
        self.dumpAcc("Rw", o)



class AstFuncDecl(AstDecl):

    ident = None
    annots = None
    args = None
    returnType = None
    body = None

    def __init__(self):
        self.annots = []
        self.args = []


    def dump(self, o):
        o.fl("Func %s", self.ident)
        o.push("{")
        for annot in self.annots:
            o.f("Annot ")
            annot.dump(o)
            o.l()
        for arg in self.args:
            o.f("Arg ")
            arg.dump(o)
            o.l()
        if self.returnType:
            o.f("Return : ")
            self.returnType.dump(o)
            o.l()
        else:
            o.fl("Return : void")
        if self.body:
            o.pl("Body")
            self.body.dump(o)
        o.pop("}")



class AstOpDecl(AstFuncDecl):

    ident = None
    args = None
    returnType = None
    body = None

    def __init__(self):
        self.args = []


    def dump(self, o):
        o.fl("Op %s", self.ident)
        o.push("{")
        
        if self.args is None:
            o.pl("Auto args")
        else:
            for arg in self.args:
                o.f("Arg ")
                arg.dump(o)
                o.l()
                
        if self.returnType:
            o.f("Return")
            self.returnType.dump(o)
            o.l()
        else:
            o.fl("Return auto")

        if self.body:
            o.pl("Body")
            self.body.dump(o)
            
        o.pop("}")



class AstAnnotScope(AstDecl):

    annots = None
    decls = None

    def __init__(self):
        self.annots = []
        self.decls = []


    def dump(self, o):
        o.fl("AnnotScope")
        o.push("{")
        for annot in self.annots:
            o.f("Annot ")
            annot.dump(o)
            o.l()
        o.push("{")
        for decl in self.decls:
            decl.dump(o)
        o.pop("}")
        o.pop("}")



class AstAnnot(AstNode):

    ident = None

    def dump(self, o):
        o.p(self.ident)



class AstArgument(AstNode):

    ident = None
    annots = None
    type = None

    def __init__(self):
        self.annots = []


    def dump(self, o):
        o.p(self.ident)
        if self.annots:
            o.p(" [")
            self.annots[0].dump(o)
            for annot in self.annots[1:]:
                o.p(", ")
                annot.dump(o)
            o.p("]")
        o.p(" : ")
        self.type.dump(o)



class AstType(AstNode):
    pass



class AstSymbolType(AstType):

    ident = None

    def dump(self, o):
        o.p(self.ident)



class AstArrayType(AstType):

    elemType = None

    def dump(self, o):
        self.elemType.dump(o)
        o.p("[]")



class AstMixin(AstDecl):

    code = None

    def dump(self, o):
        o.pl("Mixin")
        o.p("<{")
        o.depth += 1
        o.p(self.code)
        o.depth -= 1
        o.l()
        o.pl("}>")



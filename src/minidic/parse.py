
from ast import *
from source import *
from tokens import *
from lexer import *


class ParseException(Exception):

    toksrc = None
    msg = None

    def __init__(self, toksrc, msg):
        self.toksrc = toksrc
        self.msg = msg
        super(ParseException, self).__init__(str(self))


    def __str__(self):
        return "%s(%r,%r): %s" % (self.toksrc.name,
                                  self.toksrc.line+1,
                                  self.toksrc.column+1,
                                  self.msg)



class LexStream(object):
    buffer = None
    iter = None

    def __init__(self, src_or_iter):
        if isinstance(src_or_iter, Source):
            self.iter = lexIter(src_or_iter)
        else:
            self.iter = src
            
        self.buffer = []


    def peek(self, n=0):
        assert n >= 0
        if self.iter is not None and len(self.buffer) <= n:
            for tok in self.iter:
                self.buffer.append(tok)
                if len(self.buffer) > n:
                    return self.buffer[-1]

            self.iter = None

            if len(self.buffer) <= n:
                return TOKnone

        elif len(self.buffer) <= n:
            return TOKnone

        else:
            return self.buffer[n]


    def err(self, src, msg):
        raise ParseException(src, msg)


    def pop(self):
        if len(self.buffer) > 0:
            t = self.buffer[0]
            self.buffer = self.buffer[1:]
            return t

        elif self.iter is not None:
            return self.iter.next()

        else:
            assert False, "can't pop when there's nothing left!"


    def expect(self, tok, msg=None):
        actual = self.peek()
        if actual.type != tok:
            raise ParseException(
                actual.src,
                msg if msg is not None
                else "unexpected token '%s'" % actual.type[3:])


    def popExpect(self, tok, msg=None):
        actual = self.pop()
        if actual.type != tok:
            raise ParseException(
                actual.src,
                (msg if msg is not None
                 else "expected '%s', got '%s'" % (tok[3:], actual.type[3:])))

        return actual



def parseStart(ls):
    if ls.peek().type == TOKmodule:
        root = parseModuleDecl(ls)

    elif ls.peek().type == TOKpackage:
        root = parsePackageDecl(ls)

    else:
        ls.err("expected 'module' or 'package', got '%s'"
               % ls.peek().type[3:])

    while ls.peek().type != TOKeof:
        root.decls.append(parseDecl(ls))

    return root


def parseModuleDecl(ls):
    tok = ls.popExpect(TOKmodule)
    modNode = AstModule()
    modNode.src = tok.src
    modNode.fqi = parseFQI(ls)
    ls.popExpect(TOKsemi)
    return modNode


def parsePackageDecl(ls):
    tok = ls.popExpect(TOKpackage)
    pkgNode = AstPackage()
    pkgNode.src = tok.src
    pkgNode.fqi = parseFQI(ls)
    ls.popExpect(TOKsemi)
    return pkgNode


def parseFQI(ls):
    fqi = parseIdentifier(ls)
    while ls.peek().type == TOKdot:
        ls.pop()
        fqi += u"." + parseIdentifier(ls)
    return fqi


def parseIdentifier(ls):
    return ls.popExpect(TOKident).value


def parseDecl(ls):
    decl = (
        tryParseImportDecl(ls)
        or tryParseConstDecl(ls)
        or tryParseClassDecl(ls)
        or tryParseStructDecl(ls)
        or tryParseRoDecl(ls)
        or tryParseRwDecl(ls)
        or tryParseFuncDecl(ls)
        or tryParseOpDecl(ls)
        or tryParseAnnotScope(ls)
        or tryParseMixin(ls)
        or None)

    if decl is None:
        ls.err(ls.peek().src, "expected declaration, "
               +"got '%s'" % ls.peek().type[3:])

    return decl


def tryParseImportDecl(ls):
    if ls.peek().type != TOKimport: return

    decl = AstImportDecl()
    decl.src = ls.pop().src

    if ls.peek().type == TOKpackage:
        ls.pop()
        decl.isPackage = True

    decl.module = parseFQI(ls)
    if ls.peek().type == TOKcolon:
        ls.pop()
        decl.symbol = parseIdentifier(ls)

    ls.popExpect(TOKsemi)

    return decl


def tryParseConstDecl(ls):
    if ls.peek().type != TOKconst: return

    decl = AstConstDecl()
    decl.src = ls.pop().src
    decl.ident = parseIdentifier(ls)
    decl.type = parseTypeConstraint(ls)
    ls.popExpect(TOKsemi)

    return decl


def tryParseClassDecl(ls):
    if ls.peek().type != TOKclass: return

    tok = ls.pop()
    agrgDecl = parseAggregateDecl(ls)
    agrgDecl.src = tok.src
    return agrgDecl.copyAs(AstClassDecl)


def tryParseStructDecl(ls):
    if ls.peek().type != TOKstruct: return

    tok = ls.pop()
    agrgDecl = parseAggregateDecl(ls)
    agrgDecl.src = tok.src
    return agrgDecl.copyAs(AstStructDecl)


def tryParseRoDecl(ls):
    if ls.peek().type != TOKro: return

    tok = ls.pop()
    acsrDecl = parseAccessorDecl(ls)
    acsrDecl.src = tok.src
    return acsrDecl.copyAs(AstRoDecl)


def tryParseRwDecl(ls):
    if ls.peek().type != TOKrw: return

    tok = ls.pop()
    acsrDecl = parseAccessorDecl(ls)
    acsrDecl.src = tok.src
    return acsrDecl.copyAs(AstRwDecl)


def tryParseFuncDecl(ls):
    if ls.peek().type != TOKfunc: return

    func = AstFuncDecl()
    func.src = ls.pop().src
    func.ident = ls.popExpect(TOKident).value
    func.annots = tryParseAnnotations(ls) or []
    func.args = parseArgumentList(ls)
    func.returnType = tryParseTypeConstraint(ls)
    func.body = parseBody(ls)

    return func


def tryParseOpDecl(ls):
    if ls.peek().type != TOKop: return

    op = AstOpDecl()
    op.src = ls.pop().src
    op.ident = ls.popExpect(TOKident).value
    op.args = tryParseOpArgs(ls)
    op.returnType = tryParseTypeConstraint(ls)
    op.body = parseBody(ls)

    return op


def tryParseAnnotScope(ls):
    annots = tryParseAnnotations(ls)
    if annots is None: return None

    ansc = AstAnnotScope()
    ansc.annots = annots
    
    ansc.src = ls.popExpect(TOKlbrace).src
    while ls.peek().type != TOKrbrace:
        ansc.decls.append(parseDecl(ls))
    ls.popExpect(TOKrbrace)

    return ansc


def tryParseMixin(ls):
    if ls.peek().type != TOKmixin: return

    mixin = AstMixin()
    mixin.src = ls.pop().src
    mixin.code = ls.popExpect(TOKcode).tokValue
    return mixin


def parseAggregateDecl(ls):
    # DO NOT set src; this is set by the caller
    agrg = AstAggregateDecl()
    agrg.ident = ls.popExpect(TOKident).value
    agrg.annots = tryParseAnnotations(ls)
    ls.popExpect(TOKlbrace)
    while ls.peek().type != TOKrbrace:
        agrg.decls.append(parseDecl(ls))
    ls.popExpect(TOKrbrace)

    return agrg


def tryParseAnnotations(ls):
    if ls.peek().type != TOKlbracket: return None
    annots = []
    ls.pop()
    while True:
        annots.append(parseAnnotation(ls))
        if ls.peek().type == TOKrbracket:
            break
        elif ls.peek().type == TOKcomma:
            ls.pop()
            continue
        else:
            ls.err(nextTok.src, "expected ')' or ',', got '%s'" % nextTok.type[3:])
    ls.popExpect(TOKrbracket)

    return annots


def parseAnnotation(ls):
    annot = AstAnnot()
    tok = ls.popExpect(TOKident)
    annot.src = tok.src
    annot.ident = tok.value
    return annot


def parseAccessorDecl(ls):
    # DO NOT set src; this is set by caller
    acsr = AstAccessorDecl()
    acsr.ident = parseIdentifier(ls)
    ls.popExpect(TOKcolon)
    acsr.type = parseType(ls)
    ls.popExpect(TOKsemi)

    return acsr


def tryParseArgumentList(ls):
    if ls.peek().type != TOKlparen: return
    return parseArgumentList(ls)


def parseArgumentList(ls):
    args = []
    
    ls.popExpect(TOKlparen)

    if ls.peek().type != TOKrparen:
        while True:
            args.append(parseArgument(ls))
            nextTok = ls.peek()
            if nextTok.type == TOKrparen:
                break
            elif nextTok.type == TOKcomma:
                ls.pop()
            else:
                ls.err(nextTok.src,
                       "expected ')' or ',', got '%s'" % nextTok.type[3:])

    ls.popExpect(TOKrparen)

    return args


def tryParseOpArgs(ls):
    if ls.peek().type != TOKlparen: return

    ls.popExpect(TOKlparen)
    if ls.peek().type == TOKrparen:
        ls.pop()
        return None

    args = []

    while True:
        ls.popExpect(TOKcolon)
        
        arg = AstArgument()
        arg.type = parseType(ls)
        args.append(arg)
        
        nextTok = ls.peek()
        if nextTok.type == TOKrparen:
            break
        elif nextTok.type == TOKcomma:
            ls.pop()
            continue
        else:
            ls.err(nextTok.src,
                   "expected ')' or ',', got '%s'" % nextTok.type[3:])

    ls.popExpect(TOKrparen)

    return args


def parseArgument(ls):
    arg = AstArgument()
    tok = ls.popExpect(TOKident)
    arg.src = tok.src
    arg.ident = tok.value
    arg.annots = tryParseAnnotations(ls) or []
    arg.type = parseTypeConstraint(ls)
    return arg


def parseBody(ls):
    if ls.peek().type == TOKsemi:
        ls.pop()
        return None

    body = AstMixin()
    body.src = ls.peek().src
    body.code = ls.popExpect(TOKcode).tokValue
    return body


def tryParseTypeConstraint(ls):
    if ls.peek().type != TOKcolon: return
    return parseTypeConstraint(ls)


def parseTypeConstraint(ls):
    ls.popExpect(TOKcolon)
    return parseType(ls)


def parseType(ls):
    src = ls.peek().src
    ident = parseIdentifier(ls)
    type = AstSymbolType()
    type.src = src
    type.ident = ident
    
    if ls.peek().type == TOKlbracket:
        ls.popExpect(TOKlbracket)
        ls.popExpect(TOKrbracket)
        newType = AstArrayType()
        # Reuse earlier src location
        newType.src = src
        newType.elemType = type
        type = newType

    return type

    


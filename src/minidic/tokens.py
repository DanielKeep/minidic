
#__all__ = ["TOKENS", "Token"]

LITERAL_TOKENS = dict((u"TOK"+p,p) for p in u"""
    class
    const
    enum
    func
    import
    module
    mixin
    op
    package
    ro
    rw
    struct
""".split())

LITERAL_TOKENS_REV = dict((v,k) for (k,v) in LITERAL_TOKENS.iteritems())

SYMBOL_TOKENS = dict((u"TOK"+a,b) for (a,b) in (p.split(u"=",1) for p in u"""
    colon=:
    comma=,
    dot=.
    equals==
    lbrace={
    lbracket=[
    lparen=(
    rbrace=}
    rbracket=]
    rparen=)
    semi=;
""".split()))

SYMBOL_TOKENS_REV = dict((v,k) for (k,v) in SYMBOL_TOKENS.iteritems())

SYMBOL_TOKENS_ORDER = list(sorted(SYMBOL_TOKENS.itervalues(),
                                  cmp=lambda a,b: -(len(b)-len(a))))

TOKENS = u"""
TOKnone
TOKeof
TOKstring
TOKident
TOKcode
""".split() + LITERAL_TOKENS.keys() + SYMBOL_TOKENS.keys()

for tokName in TOKENS:
    globals()[tokName] = tokName
    #__all__.append(tokName)



class Token(object):

    type = None
    value = None
    tokValue = None
    src = None

    def __init__(self, type, src, value=None, tokValue=None):
        self.type = type
        self.src = src
        self.value = value
        self.tokValue = tokValue


    def __repr__(self):
        return "<%s:%r,%r%s>" % (self.type,
                                  self.src.line+1,
                                  self.src.column+1,
                                  ":%s" % repr(self.value)
                                      if self.value is not None
                                      else "")




import codecs
import itertools
import unicodedata

from source import *
from tokens import *



def isNl(str):
    if str.startswith("\r\n"):
        return 2
    elif str[0] in "\r\n":
        return 1
    else:
        return 0


def isWs(str):
    return str[0] in u" \t\r\n\f\v"


def isHex(str):
    return str[0] in u"0123456789abcdefABCDEF"


def isOctal(str):
    return str[0] in u"01234567"


def lexBlockComment(osrc):
    src = osrc
    if src[:2] == "/*":
        src = src.advanced(2)
        while len(src) >= 2:
            if src[:2] == "*/":
                return src.advanced(2), None
            else:
                src.advance(1)

        return None, osrc.err("unterminated block comment")

    else:
        return None, None


def lexLineComment(osrc):
    src = osrc
    if src[:2] == "//":
        src = src.advanced(2)
        while len(src) > 0:
            nl = isNl(src[:2])
            if nl > 0:
                src.advance(nl)
                return src, None
            else:
                src.advance(1)

        return src, None

    else:
        return None, None


def lexNestedComment(osrc):
    src = osrc
    if src[:2] == "/+":
        depth = 1
        src = src.advanced(2)
        while len(src) >= 2:
            s2 = src[:2]
            if s2 == "/+":
                depth += 1
                src.advance(2)
                
            elif s2 == "+/":
                depth -= 1
                src.advance(2)
                if depth == 0:
                    return src, None

            else:
                src.advance(1)

        return None, osrc.err("unterminated nested comment")

    else:
        return None, None


def lexComment(src):
    for lexFn in (lexBlockComment, lexLineComment, lexNestedComment):
        ns,tok = lexFn(src)
        if ns or tok: return ns,tok

    return None, None


def skipWhitespace(src):
    while isWs(src[0]):
        src.advance(1)


UNI_LETTER_CG = ('Lu', 'Ll', 'Lt')


def ucc(s):
    return unicodedata.category(unicode(s))


def isIdentStart(s):
    return s == u"_" or ucc(s) in UNI_LETTER_CG


def isIdent(s):
    return isIdentStart(s) or s in u"0123456789"


def lexIdentifier(osrc):
    src = osrc
    if isIdentStart(src[0]):
        src = src.advanced(1)
        while isIdent(src[0]):
            src.advance(1)

        v = osrc.until(src)
        if v in LITERAL_TOKENS_REV:
            return src, Token(LITERAL_TOKENS_REV[v], osrc)
        else:
            return src, Token(TOKident, osrc, osrc.until(src))

    else:
        return None, None


def lexLiteral(osrc):
    src = osrc
    for tok in SYMBOL_TOKENS_ORDER:
        if src.startswith(tok):
            return (src.advanced(len(tok)),
                    Token(SYMBOL_TOKENS_REV[tok], osrc))

    return None, None


def lexString(osrc):
    src = osrc
    if len(src) < 2: return None, None

    c = src[0]
    c1 = src[1]

    n = [0]

    def eatStringChars(allowescape, hexonly, term):
        r = u""
        mark = n[0]

        while True:
            if n[0] == len(src):
                return None, osrc.err("unterminated string literal")

            eol = isNl(src[n[0]:n[0]+2])
            if eol != 0:
                n[0] += eol
                continue

            esc,escVal,escErr = 0,None,None
            if allowescape:
                esc,escVal,escErr = isEscapeSequence(src[:10])
                if escErr:
                    return None, src.advanced(n[0]+esc).err(escErr)

            if esc != 0:
                r += src[mark:n[0]]
                r += escVal
                mark = n+esc
                n[0] += esc
                continue

            c = src[n[0]]
            if hexonly and not isHex(c) and not isWhitespace(c) and c != term:
                return None, src.advanced(n[0]).err("found invalid character '%r' in hex string" % c)

            n[0] += 1
            if c == term:
                r += src[mark:n[0]-1]
                break

        return r, None

    # wysiwyg
    if c == 'r' and c1 == '"':
        n[0] = 2
        r,e = eatStringChars(False, False, '"')
        if r is None: return r,e

    elif c == '`':
        n[0] = 1
        r,e = eatStringChars(False, False, '`')
        if r is None: return r,e

    # hex string
    elif c == 'x' and c1 == '"':
        n[0] = 2
        r,e = eatStringChars(False, True, '"')
        if r is None: return r,e
        hexstr = decodeHexString(r)
        if hexstr is None:
            return None, osrc.err("odd number of nybbles in hex string")

        r = hexstr

    # double quotes
    elif c == '"':
        n[0] = 1
        r,e = eatStringChars(True, False, '"')
        if r is None: return r,e

    # Found one
    if n[0] > 0:
        return osrc.advanced(n[0]), Token(TOKstring, osrc, osrc[:n[0]], r)

    else:
        return None, None


def decodeHexString(str):
    acc = None
    r = bytes()

    for c in str:
        if not isHex(c):
            continue

        if acc is None:
            acc = int(c, 16)

        else:
            r += chr(acc*16 + int(c,16))
            acc = None

    if acc is None:
        return r
    else:
        return None


BASIC_ESCAPES = {
    '\'': "'",
    '"' : "\"",
    '?' : "\x1b",
    "\\": "\\",
    "a" : "\a",
    "b" : "\b",
    "f" : "\f",
    "n" : "\n",
    "r" : "\r",
    "t" : "\t",
    "v" : "\v",
}


def isEscapeSequence(str):
    n = 0
    c = str[n]
    if c == '\\':
        n += 1
        c = str[n]
        if c in BASIC_ESCAPES:
            n += 1
            return n, BASIC_ESCAPES[c], None

        elif c == 'x':
            n += 1
            c = str[n]
            for i in range(2):
                if( not isHex(c) ):
                    return (n, None,
                            "invalid \\x escape sequence - found %r" % c)

                n += 1
                c = str[n]

            return n, unichr(int(str[3:5],16)), None

        elif c == 'u':
            n += 1
            c = str[n]
            for i in range(4):
                if( not isHex(c) ):
                    return (n, None,
                            "invalid \\u escape sequence - found %r" % c)

                n += 1
                c = str[n]

            return n, unichr(int(str[3:3+4],16)), None

        elif c == 'U':
            n += 1
            c = str[n]
            for i in range(4):
                if( not isHex(c) ):
                    return (n, None,
                            "invalid \\u escape sequence - found %r" % c)

                n += 1
                c = str[n]

            return n, unichr(int(str[3:3+8],16)), None

        elif c in u"01234567":
            n += 1
            c = str[n]
            for i in range(3):
                if not isOctal(c):
                    break

                n += 1
                c = str[n]

            return n, unichr(int(str[3:n], 8)), None

        elif c == '&':
            return n, None, 'named character entity escape sequences are not yet implemented'

        else:
            return (n, None,
                    "invalid escape sequence"
                    +" - unexpected character %r found" % c)

    return 0, None, None


def lexEof(osrc):
    if len(osrc) == 0:
        return osrc, Token(TOKeof, osrc)

    return None, None


def lexCode(osrc):
    src = osrc
    if src[:2] == "<{":
        src = src.advanced(2)
        while len(src) >= 2:
            if src[:2] == "}>":
                src.advance(2)
                v = osrc.until(src)
                return src, Token(TOKcode, src, v, v[2:-2])

            src.advance(1)

        return None, osrc.err("unterminated code literal")

    else:
        return None, None


LEX_FNS = (
    lexEof,
    lexIdentifier,
    lexLiteral,
    lexString,
    lexCode,
)


def lexIter(osrc):
    src = osrc
    while True:
        #print 'skip %r' % src[:]
        skipWhitespace(src)
        #print 'comment %r' % src[:]
        ns,tok = lexComment(src)
        if ns:
            src = ns
            continue
        elif tok:
            raise tok

        gotTok = False

        for lexFn in LEX_FNS:
            #print 'try %r(%r)' % (lexFn, src[:])
            ns,tok = lexFn(src)
            if ns:
                #print 'lex %r, %r' % (ns[:], tok)
                gotTok = True
                yield tok
                if tok.type == TOKeof:
                    return
                src = ns
                break
            elif tok:
                #print 'err %r' % tok
                raise tok

        if not gotTok:
            raise src.err("unknown token")


def dumplex(src):
    for tok in lexIter(Source('-', unicode(src))):
        print 'token %r' % tok


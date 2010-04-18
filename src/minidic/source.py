
import codecs


class SourceException(Exception):
    source = None
    msg = None

    def __init__(self, source, msg):
        self.source = source
        self.msg = msg
        super(SourceException, self).__init__(str(self))


    def __str__(self):
        return '%s(%d,%d): %s' % (
            self.source.name,
            self.source.line+1,
            self.source.column+1,
            self.msg)



class Source(object):
    text = None
    name = None
    offset = None
    line = None
    column = None

    last_cp_was_cr = False

    def __init__(self, name, text=None):
        if text is None:
            inf = codecs.open(name, encoding='utf-8')
            text = inf.read()
            inf.close()

        self.name = name
        self.text = text
        self.offset = 0
        self.line = 0
        self.column = 0


    def __str__(self):
        return "%s:%s,%s" % (self.name, self.line+1, self.column+1)


    def __getitem__(self, i):
        if isinstance(i, slice):
            assert i.step in (None, 1)
            start,stop,_ = i.indices(len(self.text))
            r = self.text[self.offset+start:self.offset+stop]
            if i.stop is not None and len(r) < i.stop-(i.start or 0):
                return r + u"\ufffe"*((i.stop-(i.start or 0))-len(r))
            else:
                return r

        else:
            if self.offset+i >= len(self.text):
                return u"\ufffe"
            else:
                return self.text[self.offset+i]


    def __len__(self):
        return len(self.text) - self.offset


    def __nonzero__(self):
        return True


    def until(self, src):
        return self.text[self.offset:src.offset]


    def startswith(self, s):
        return self[:len(s)] == s


    def advance(self, chars):
        lineInc = 0
        column = self.column
        cr = self.last_cp_was_cr

        advText = self[:chars]
        
        for char in advText:
            if char == '\r':
                cr = True
                lineInc += 1
                column = 0

            elif char == '\n':
                if cr:
                    cr = False
                else:
                    lineInc += 1
                    column = 0

            else:
                cr = False
                column += 1

        self.offset += len(advText)
        self.line += lineInc
        self.column = column
        self.last_cp_was_cr = cr


    def advanced(self, chars):
        r = self.copy()
        r.advance(chars)
        return r


    def copy(self):
        r = Source(self.name, self.text)
        r.offset = self.offset
        r.line = self.line
        r.column = self.column
        return r


    def err(self, msg, *pargs):
        if len(pargs) > 0:
            msg = msg % pargs
        return SourceException(self, msg)



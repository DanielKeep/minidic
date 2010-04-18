

class Writer(object):

    def __init__(self, os=None):
        if os is None:
            import sys
            os = sys.stdout
        self.os = os
        self.depth = 0
        self.indented = False

    def r(self, s):
        self.os.write(s)
        return self

    def rf(self, fmt, *pargs):
        self.r(fmt % pargs)
        return self

    def rfl(self, fmt, *pargs):
        self.rf(fmt, *pargs)
        self.r("\n")
        return self

    def rl(self, s):
        self.r(s)
        self.r("\n")
        return self

    def p(self, s):
        if not self.indented:
            self.os.write("  "*self.depth)
            self.indented = True
        self.os.write(s)
        return self

    def l(self):
        self.p("\n")
        self.indented = False
        return self

    def pl(self, s):
        self.p(s)
        self.l()
        return self

    def f(self, fmt, *pargs):
        self.p(fmt % pargs)
        return self

    def fl(self, fmt, *pargs):
        self.f(fmt, *pargs)
        self.l()
        return self

    def push(self, s=None):
        if s is not None: self.pl(s)
        self.depth += 1
        return self

    def pop(self, s=None):
        self.depth -= 1
        if s is not None: self.pl(s)
        return self



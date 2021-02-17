import re


class LexerError(Exception):

    def __init__(self, msg, context):
        self.msg = msg
        self.ctx = context


class Lexer:

    def __init__(self, l=None):
        self.l = l
        self._ws = re.compile("[ \t]+")

    def init(self, l):
        self.l = l

    def error(self, msg, ctx=None):
        if ctx is None:
            ctx = self.l
        raise LexerError(msg, ctx)

    def eol(self):
        return not self.l

    def skipws(self):
        m = self._ws.match(self.l)
        if m:
            self.l = self.l[m.end():]

    def check(self, s):
        return self.l.startswith(s)

    def match(self, s, skipws=True):
        if self.check(s):
            self.l = self.l[len(s):]
            if skipws:
                self.skipws()
            return True

    def match_re(self, r, skipws=True):
        m = r.match(self.l)
        if m:
            self.l = self.l[m.end():]
            if skipws:
                self.skipws()
            return m.group()

    def expect(self, s, skipws=True):
        res = self.match(s, skipws)
        if res:
            return res
        self.error("Expected %r" % s)

    def expect_re(self, r, skipws=True, err=None):
        res = self.match_re(r, skipws)
        if res:
            return res
        if err is not None:
            self.error(err)
        else:
            self.error("Expected %r" % r)

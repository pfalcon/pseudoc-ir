# PseudoC-IR - Simple Program Analysis/Compiler Intermediate Representation
#
# Copyright (c) 2020-2021 Paul Sokolovsky
#
# The MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import re

from lexer import Lexer
from .ir import Insn, BBlock, Func, Data, Module


LEX_IDENT = re.compile(r"[@$]?[A-Za-z_][A-Za-z_0-9]*")
LEX_NUM = re.compile(r"-?\d+")
# Simplified. To avoid enumerating specific operators supported, just say
# "anything non-space".
LEX_OP = re.compile(r"[^ ]+")


def parse_var(lex):
    return lex.expect_re(LEX_IDENT, err="expected identifier")


def parse_val(lex):
    v = lex.match_re(LEX_IDENT)
    if v:
        return v
    v = lex.match_re(LEX_NUM)
    if v:
        return int(v, 0)
    lex.error("expected value (var or num)")


def parse_args(lex):
    # "(" already matched
    res = []
    while not lex.check(")"):
        res.append(parse_val(lex))
        if not lex.match(","):
            break
    lex.expect(")")
    return res


def parse_if_expr(lex):
    res = []
    lex.expect("(")
    res.append(parse_val(lex))
    if not lex.check(")"):
        res.append(lex.expect_re(LEX_OP))
        res.append(parse_val(lex))
    lex.expect(")")
    return res


def parse(f):
    mod = Module()
    bb = None
    prev_bb = None
    label2bb = {}
    lex = Lexer()
    cfg = None

    def get_bb(label):
        bb = label2bb.get(label)
        if bb is None:
            bb = label2bb[label] = BBlock(label, [])
        return bb

    for l in f:
        l = l.strip()
        if not l or l.startswith("#"):
            continue

        lex.init(l)

        if cfg is None:
            name = lex.expect_re(LEX_IDENT)
            if lex.match("("):
                cfg = Func(name)
                cfg.params = parse_args(lex)
                lex.expect("{")
                label2bb = {}
                bb = None
                prev_bb = None
            elif lex.match("="):
                mod.contents.append(Data(name, lex.l))
            else:
                lex.error("expected function or data definition")
            continue

        if lex.match("}"):
            cfg.calc_preds()
            mod.contents.append(cfg)
            cfg = None
            continue

        if l.endswith(":"):
            label = l[:-1]
            if True:
                bb = get_bb(label)
                cfg.bblocks.append(bb)
                if prev_bb:
                    # Fallthru edge
                    prev_bb.succs.append(bb)
                prev_bb = bb
            continue

        insn = None

        # Context before having parsed anything, for error messages.
        lex_ctx = lex.l

        if lex.match("goto"):
            label = lex.expect_re(LEX_IDENT)
            bb.succs.append(get_bb(label))
            prev_bb = None

        elif lex.match("if"):
            expr = parse_if_expr(lex)
            lex.expect("goto")
            label = lex.expect_re(LEX_IDENT)
            bb.succs.append(get_bb(label))
            if not lex.eol():
                lex.expect("else")
                # Currently "goto" after "else" is optional.
                lex.match("goto")
                label = lex.expect_re(LEX_IDENT)
                bb.succs.append(get_bb(label))
                prev_bb = None
            insn = Insn("", "if", *expr)

        elif lex.match("return"):
            if not lex.eol():
                arg = parse_val(lex)
                insn = Insn("", "return", arg)
            else:
                insn = Insn("", "return")
            prev_bb = None

        else:
            dest = parse_var(lex)

            if lex.match("="):
                if not dest.startswith("$"):
                    lex.error("Can assign only to local variables (must start with '$')", ctx=lex_ctx)

                arg1 = parse_val(lex)
                if lex.eol():
                    insn = Insn(dest, "=", arg1)
                else:
                    op = lex.expect_re(LEX_OP)
                    if op == "(":
                        args = parse_args(lex)
                        insn = Insn(dest, arg1, *args)
                    else:
                        arg2 = parse_val(lex)
                        insn = Insn(dest, op, arg1, arg2)
            elif lex.match("("):
                # Function call
                args = parse_args(lex)
                insn = Insn("", dest, *args)
            else:
                lex.error("Unexpected syntax")

        assert lex.eol(), "Unexpected content at end of line: %r" % lex.l

        if insn:
            bb.insns.append(insn)

    #print(label2bb)
    #print(cfg.bblocks)
    #cfg.simple_print()

    return mod


def __main__():
    with open(sys.argv[1]) as f:
        mod = parse(f)
        mod.dump(bb_ann=False, expl_goto=True)


if __name__.startswith("__main__"):
    import sys

if __name__ == "__main__":
    __main__()

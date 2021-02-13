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

from . import ir


# Insn functions


def is_infix_op(self):
    return not self.op[0].isalpha() and not self.op.startswith("@") and len(self.args) == 2


def format_dest_name(self, is_ssa=True):
    n = self.dest
    if is_ssa:
        n += "_%s" % self.id
    reg = "{%s}" % self.reg if self.reg else ""
    return n + reg


def format_args(args=None, sep=", "):
    return sep.join([str(a) for a in args])


def format_if_insn(self):
    "Format inital part of the 'if' instruction."
    return "%s (%s)" % (self.op, format_args(self.args, sep=" "))


def format_insn(self, bb=None, is_ssa=True):
    "Format textual mnemonic of instruction, without any annotations."
    res = ""

    if self.dest:
        if self.typ:
            res += "%s " % self.typ
        res += "%s = " % format_dest_name(self, is_ssa)

    if is_infix_op(self):
        res += "%s %s %s" % (self.args[0], self.op, self.args[1])
    elif self.op == "=":
        res += format_args(self.args)
    elif self.op == "@nop":
        res += self.op
    elif self.op == "@load":
        if self.args[1].val is None:
            res += "*%s" % self.args[0]
        else:
            assert isinstance(self.args[1].val, ir.Type), repr(self.args[1])
            res += "*(%s*)%s" % (self.args[1].val, self.args[0])
    elif self.op == "@store":
        if self.args[1].val is None:
            res += "*%s = %s" % (self.args[0], self.args[2])
        else:
            assert isinstance(self.args[1].val, ir.Type), repr(self.args[1])
            res += "*(%s*)%s = %s" % (self.args[1].val, self.args[0], self.args[2])
    elif self.op.startswith("@"):
        res += "%s(%s)" % (self.op, format_args(self.args))
    elif self.op == "call":
        res += "%s(%s)" % (self.args[0], format_args(self.args[1:]))
    elif self.op == "if":
        res += format_if_insn(self)
        if bb:
            assert len(bb.succs) == 2
            res += " goto %s else %s" % (bb.succs[0].label, bb.succs[1].label)
    elif self.op == "goto":
        if bb:
            assert len(bb.succs) == 1
            res += "%s %s" % (self.op, bb.succs[0].label)
        else:
            res += "%s %s" % (self.op, format_args(self.args))
    else:
        res += self.op
        args = format_args(self.args)
        if args:
            res += " " + args

    return res


# __str__ alike which can take extra optional args.
def format_insn_ann(self, bb=None, **opts):
    prefix = "    "
    suffix = ""
    if self.id is not None:
        prefix = "%6d: " % self.id
    mnem = self.format_insn(bb, **opts)
    if suffix:
        suffix = " ;" + suffix
    return prefix + mnem + suffix


# Arg functions


def format_arg(self):
    if self.defi is not None:
        return self.defi.dest_name()
    else:
        n = str(self.val)
        reg = "{%s}" % self.reg if self.reg else ""
        return n + reg


# BBlock functions


def dump_bb_insns(self, file=None, **opts):
    for s in self.insns:
        print(s.to_str(bb=self, **opts), file=file)


def dump_bb(self, bb_ann=True, expl_goto=False, file=None, **opts):
    print("%s:" % self.label, file=file)
    if bb_ann:
        print("    # pred: %s" % (
            [b.label for b in self.preds],
        ), file=file)
    dump_bb_insns(self, file=file, **opts)
    if expl_goto and len(self.succs) == 1:
        print("    goto %s" % self.succs[0].label, file=file)
    if bb_ann:
        print("    # succ: %s" % (
            [b.label for b in self.succs],
        ), file=file)


# Func functions


def format_func_params(self, params, param_types):
    if any(param_types):
        pt = ", ".join(["%s %s" % p for p in zip(param_types, params)])
    else:
        pt = ", ".join(["%s" % p for p in params])
    return pt


def dump_func(self, file=None, **opts):
    t = ""
    if self.res_type:
        t = "%s " % self.res_type
    param_str = format_func_params(self, self.params, self.param_types)
    print("%s%s(%s) {" % (t, self.name, param_str), file=file)
    for bb in self.bblocks:
        bb.dump(file=file, is_ssa=self.is_ssa, **opts)
    print("}", file=file)


# For debugging during parsing only
def simple_dump_func(self):
    for bb in self.bblocks:
        bb.simple_print()


# Struct functions


def dump_struct(self, file=None, **opts):
    print("struct %s { " % self.name, end="", file=file)
    need_comma = False
    for name, typ in self.fields:
        if need_comma:
            print(", ", end="", file=file)
        print("%s" % typ, end="", file=file)
        if name:
            print(" %s" % name, end="", file=file)
        need_comma = True
    print(" }", file=file)


# Data functions


def dump_data(self, file=None, **opts):
    print("%s = %s" % (self.name, self.desc), file=file)


# Module functions


def dump_module(self, file=None, **opts):
    need_empty_line = False
    for item in self.contents:
        if need_empty_line:
            print(file=file)
        item.dump(file=file, **opts)
        need_empty_line = True

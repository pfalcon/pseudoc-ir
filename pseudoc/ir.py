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

import logging

from . import dumper


_log = logging.getLogger(__name__)


class Arg:

    def __init__(self, val):
        self.val = val
        self.defi = None

    def __repr__(self):
        return "<Arg '%s'>" % self.__str__()

    __str__ = dumper.format_arg


class Insn:

    def __init__(self, dest, op, *args, type=None):
        self.id = None
        # Data type of dest ("u32", etc.)
        self.typ = type
        self.dest = dest
        self.op = op
        self.args = [Arg(val) for val in args]

    def __repr__(self):
        return "<Insn @%s>" % self.dest_name()

    dest_name = dumper.format_dest_name
    format_insn = dumper.format_insn
    # to_str allows to pass extra optional args.
    __str__ = to_str = dumper.format_insn_ann


class BBlock:

    def __init__(self, label, insns=None):
        self.label = label
        if insns is None:
            insns = []
        self.insns = insns
        self.preds = []
        self.succs = []

    def __repr__(self):
        return "<BBlock %s>" % self.label

    dump_insns = dumper.dump_bb_insns
    dump = dumper.dump_bb


class Func:

    def __init__(self, name):
        self.name = name
        self.res_type = None
        self.params = ()
        self.param_types = ()
        self.bblocks = []

    def __repr__(self):
        return "<Func %s %d bb>" % (self.name, len(self.bblocks))

    dump = dumper.dump_func


class Type:
    pass


class PrimType(Type):
    def __init__(self, typ):
        self.typ = typ

    def __str__(self):
        return self.typ


class PtrType(Type):
    def __init__(self, el_type):
        self.el_type = el_type

    def __str__(self):
        return "%s*" % self.el_type


class ArrType(Type):
    def __init__(self, el_type, num):
        self.el_type = el_type
        self.num = num

    def __str__(self):
        idxs = ""
        t = self
        # "Reverse" order of recursive array types to get C-like notation.
        while isinstance(t, ArrType):
            idxs += "[%d]" % t.num
            t = t.el_type
        return "%s%s" % (t, idxs)


class StructType(Type):
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields  # (name, type)

    def __str__(self):
        return "struct %s" % self.name

    dump = dumper.dump_struct


class Data:

    def __init__(self, name, desc, type=None):
        self.name = name
        self.desc = desc
        self.type = type

    def __repr__(self):
        return "<Data %s>" % self.name

    dump = dumper.dump_data


class Module:

    def __init__(self):
        self.contents = []

    def add(self, item):
        self.contents.append(item)

    dump = dumper.dump_module

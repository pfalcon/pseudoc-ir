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


_log = logging.getLogger(__name__)


class Arg:

    def __init__(self, val):
        self.val = val
        self.defi = None


class Insn:

    def __init__(self, dest, op, *args, type=None):
        self.id = None
        # Data type of dest ("u32", etc.)
        self.typ = type
        self.dest = dest
        self.op = op
        self.args = [Arg(val) for val in args]


class BBlock:

    def __init__(self, label, insns=None):
        self.label = label
        if insns is None:
            insns = []
        self.insns = insns
        self.preds = []
        self.succs = []


class Func:

    def __init__(self, name):
        self.name = name
        self.res_type = None
        self.params = ()
        self.param_types = ()
        self.bblocks = []

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
from .ir import InlineStr, SpecFunc, Arg, Insn, BBlock, Func, Data, Module, PrimType, PtrType, ArrType, StructType


LEX_IDENT = re.compile(r"[$][A-Za-z_0-9]+|[@]?[A-Za-z_][A-Za-z_0-9]*")
LEX_SIMPLE_IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
LEX_QUOTED_IDENT = re.compile(r"`.+?`")
LEX_NUM = re.compile(r"-?\d+")
LEX_TYPE = re.compile(r"void|i1|i8|u8|i16|u16|i32|u32|i64|u64")
# Simplified. To avoid enumerating specific operators supported, just say
# "anything non-space, except handle opening parens specially (for calls
# w/o args).
LEX_OP = re.compile(r"\(|[^ ]+")
LEX_UNARY_OP = re.compile(r"[-~!*]")
LEX_STR = re.compile(r'"([^\\]|\\.)*"')

TYPE_NAMES = {"void", "i1", "i8", "u8", "i16", "u16", "i32", "u32", "i64", "u64"}


LABEL_CNT = 0
STRUCT_TYPE_MAP = {}


def parse_reg(lex, name):
    reg = None
    if name.startswith("$"):
        if lex.match("{"):
            reg = lex.expect_re(LEX_IDENT, err="expected identifier")
            lex.expect("}")
    return reg


def parse_var(lex):
    typ = parse_type(lex)
    name = lex.expect_re(LEX_IDENT, err="expected identifier")
    reg = parse_reg(lex, name)
    return typ, name, reg


def parse_type_name(lex):
    return lex.match_re(LEX_TYPE)


def parse_type_mod(lex, typ):
    while True:
        if lex.match("*"):
            typ = PtrType(typ)
        elif lex.check("["):
            dims = []
            while lex.match("["):
                dim = parse_val(lex).val
                assert isinstance(dim, int)
                dims.append(dim)
                lex.expect("]")
            for dim in reversed(dims):
                typ = ArrType(typ, dim)
        else:
            break
    return typ


def parse_type(lex):
    if lex.match("struct"):
        name = lex.expect_re(LEX_SIMPLE_IDENT, "expected structure identifier")
        typ = STRUCT_TYPE_MAP.get(name)
        if typ is None:
            typ = STRUCT_TYPE_MAP[name] = StructType(name, None)
    else:
        typ = parse_type_name(lex)
        if typ is None:
            return None
        typ = PrimType(typ)
    return parse_type_mod(lex, typ)


def parse_simple_type(lex):
    if lex.match("void"):
        lex.expect("*")
        return "void*"
    return parse_type_name(lex)


def parse_global_type_and_name(lex):
    typ = None
    name = None
    parsed = lex.match_re(LEX_QUOTED_IDENT)
    if parsed:
        # If we matched a quoted id at the beginning, we know there's no type.
        name = parsed[1:-1]
    else:
        parsed = lex.expect_re(LEX_SIMPLE_IDENT, "expected a simple identifier")
        if parsed == "struct":
            parsed = lex.expect_re(LEX_SIMPLE_IDENT, "expected structure identifier")
            typ = STRUCT_TYPE_MAP.get(parsed)
            if typ is None:
                typ = STRUCT_TYPE_MAP[parsed] = StructType(parsed, None)
        elif parsed in TYPE_NAMES:
            typ = PrimType(parsed)
        else:
            # Otherwise what we parsed is a name.
            name = parsed

        if typ:
            typ = parse_type_mod(lex, typ)
            name = lex.match_re(LEX_SIMPLE_IDENT)
            if not name:
                name = lex.match_re(LEX_QUOTED_IDENT)
            if not name:
                # If that was a bare structure name followed by {, i.e. a
                # structure type definition, it's ok to not have a name,
                # otherwise report error.
                if isinstance(typ, StructType) and lex.check("{"):
                    pass
                else:
                    lex.error("identifer expected after type")

    return (typ, name)


# Returns Arg object with .val and possibly .reg initialized.
def parse_val(lex, spec_funcs=False):
    reg = None
    v = lex.match_re(LEX_IDENT)
    if v:
        if spec_funcs and v.startswith("@"):
            if not v in ("@sizeof"):
                lex.error("Only const-valued special functions may be used where value is expected")
            lex.expect("(")
            if v == "@sizeof":
                args = [parse_type(lex)]
                lex.expect(")")
            else:
                args = parse_args(lex)
            return Arg(SpecFunc(v, *args))
        else:
            reg =  parse_reg(lex, v)
    else:
        v = lex.match_re(LEX_NUM)
        if v:
            v = int(v, 0)
        else:
            v = lex.match_re(LEX_STR)
            if v:
                v = InlineStr(v[1:-1])
            else:
                lex.error("expected value (var or const)")
    a = Arg(v)
    if reg is not None:
        a.reg = reg
    return a


def parse_args(lex):
    # "(" already matched
    res = []
    while not lex.check(")"):
        res.append(parse_val(lex, spec_funcs=True))
        if not lex.match(","):
            break
    lex.expect(")")
    return res


def parse_params(lex):
    # "(" already matched
    names = []
    types = []
    while not lex.check(")"):
        typ, name, reg = parse_var(lex)
        names.append(name)
        types.append(typ)
        if not lex.match(","):
            break
    lex.expect(")")
    return names, types


def parse_if_expr(lex):
    res = []
    lex.expect("(")
    res.append(parse_val(lex))
    if not lex.check(")"):
        res.append(lex.expect_re(LEX_OP))
        res.append(parse_val(lex))
    lex.expect(")")
    return res


def get_label():
    global LABEL_CNT
    c = LABEL_CNT
    LABEL_CNT += 1
    return "_l%d" % c


def make_call(dest, name, *args):
    if name.startswith("@"):
        # Special name
        return Insn(dest, name, *args), False
    else:
        return Insn(dest, "call", name, *args), True


TYPE_SIZES = {
    "i8": 1,
    "u8": 1,
    "i16": 2,
    "u16": 2,
    "i32": 4,
    "u32": 4,
    "i64": 8,
    "u64": 8,
    "void*": 4,
}

def parse_data(lex, name):
    desc = []
    size = 0
    lex.expect("{")
    while not lex.match("}"):
        if lex.check('"'):
            s = lex.match_re(LEX_STR)
            b = s[1:-1].encode()

            def unesc(m):
                v = m.group(0)[1:]
                if v.startswith(b"x"):
                    v = bytes([int(v[1:], 16)])
                else:
                    v = {b"0": b"\0", b'"': b'"', b"n": b"\n"}[v]
                return v
            b = re.sub(rb"(\\x..|\\.)", unesc, b)

            desc.append(("str", s, b))
            size += len(b)
        elif lex.match('('):
            typ = parse_simple_type(lex)
            lex.expect(")")
            desc.append((typ, parse_val(lex)))
            size += TYPE_SIZES[typ]
        else:
            lex.error("Unexpected syntax in data element")
        lex.match(",")
    data = Data(name, desc)
    data.size = size
    return data


def parse(f):
    STRUCT_TYPE_MAP.clear()
    mod = Module()
    bb = None
    prev_bb = None
    label2bb = {}
    lex = Lexer()
    start_new_bb = True
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
            typ, name = parse_global_type_and_name(lex)

            if isinstance(typ, StructType) and lex.match("{"):
                # Structure declaration
                if typ.fields is not None:
                    lex.error("duplicate struct definition: %s" % typ.name)
                fields = []
                while not lex.match("}"):
                    typ_fld = parse_type(lex)
                    fldname = lex.match_re(LEX_SIMPLE_IDENT)
                    fields.append((fldname, typ_fld))
                    lex.match(",")
                typ.fields = fields
                mod.add(typ)
                continue
            elif lex.match("("):
                cfg = Func(name)
                cfg.res_type = typ
                cfg.params, cfg.param_types = parse_params(lex)
                lex.expect("{")
                label2bb = {}
                start_new_bb = True
                bb = None
                prev_bb = None
            elif lex.match("="):
                data = parse_data(lex, name)
                data.type = typ
                mod.contents.append(data)
            else:
                lex.error("expected function, data, or structure definition")
            continue

        if lex.match("}"):
            cfg.calc_preds()
            mod.contents.append(cfg)
            cfg = None
            continue

        is_label = l.endswith(":")
        if is_label or start_new_bb:
            if is_label:
                label = l[:-1]
            else:
                label = get_label()
            if True:
                bb = get_bb(label)
                cfg.bblocks.append(bb)
                if prev_bb:
                    # Fallthru edge
                    prev_bb.succs.append(bb)
                prev_bb = bb
            start_new_bb = False
            if is_label:
                continue

        insn = None

        # Context before having parsed anything, for error messages.
        lex_ctx = lex.l

        if lex.match("goto"):
            label = lex.expect_re(LEX_IDENT)
            bb.succs.append(get_bb(label))
            prev_bb = None
            start_new_bb = True

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
            start_new_bb = True

        elif lex.match("return"):
            if not lex.eol():
                arg = parse_val(lex)
                insn = Insn("", "return", arg)
            else:
                insn = Insn("", "return")
            prev_bb = None

        elif lex.match("@nop"):
            insn = Insn("", "@nop")

        else:
            ptr_typ = None
            if lex.match("*"):
                lex.expect("(")
                ptr_typ = parse_type(lex)
                assert isinstance(ptr_typ, PtrType)
                ptr_typ = ptr_typ.el_type
                lex.expect(")")
            dest_typ, dest, dest_reg = parse_var(lex)

            if lex.match("="):
                if ptr_typ is None and not dest.startswith("$"):
                    lex.error("Can assign only to local variables (must start with '$')", ctx=lex_ctx)

                unary_op = lex.match_re(LEX_UNARY_OP)
                if unary_op:
                    # Unary op
                    typ = None
                    if unary_op == "*":
                        if lex.match("("):
                            typ = parse_type(lex)
                            assert isinstance(typ, PtrType)
                            typ = typ.el_type
                            lex.expect(")")
                    arg1 = parse_val(lex)
                    if unary_op == "*":
                        insn = Insn(dest, "@load", arg1, typ)
                    else:
                        insn = Insn(dest, op, arg1)
                else:
                    arg1 = parse_val(lex)
                    if lex.eol():
                        if ptr_typ is None:
                            # Move
                            insn = Insn(dest, "=", arg1)
                        else:
                            # Store
                            insn = Insn("", "@store", dest, ptr_typ, arg1)
                    else:
                        # Binary op
                        op = lex.expect_re(LEX_OP)
                        if op == "(":
                            # Function call
                            args = parse_args(lex)
                            insn, start_new_bb = make_call(dest, arg1.val, *args)
                        else:
                            arg2 = parse_val(lex)
                            insn = Insn(dest, op, arg1, arg2)
                insn.reg = dest_reg
                insn.typ = dest_typ
            elif lex.match("("):
                # Function call
                args = parse_args(lex)
                insn, start_new_bb = make_call("", dest, *args)
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

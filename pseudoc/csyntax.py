from pseudoc import config
from .ir import Func, Data


def str_varset(s):
    return ", ".join(sorted([v.dest_name() for v in s]))


def render_insn(insn, bb, cfg, use_regs):

    def str_arg(arg):
        if arg.defi is not None:
            if use_regs:
                val = arg.defi.reg
            else:
                val = arg.defi.dest_name()
        else:
            if arg.val == "@undef":
                return "UNDEF"
            val = str(arg.val)
        return val

    def format_args(insn):
        res = []
        for arg in insn.args:
            res.append(str_arg(arg))
        return ", ".join(res)

    def render(insn):
        prefix = ""

        if not insn.dest:
            if insn.op == "return":
                if insn.args:
                    return "return %s" % str_arg(insn.args[0])
                else:
                    return "return"
            elif insn.op == "goto":
                return "goto %s" % insn.args[0]
            elif insn.op == "if":
                return "if (%s) goto %s; else goto %s" % (
                    " ".join([str_arg(a) for a in insn.args]),
                    bb.succs[0].label,
                    bb.succs[1].label,
                )

        if insn.op == "@param":
            rhs = cfg.params[insn.args[0].val]
        elif insn.op == "@load":
            rhs = "*(%s*)%s" % (insn.args[1], str_arg(insn.args[0]))
        elif insn.op == "@store":
            rhs = "*(%s*)%s = %s" % (insn.args[1], str_arg(insn.args[0]), str_arg(insn.args[2]))
        elif insn.op == "@phi":
            if use_regs:
                reg = insn.reg
                for a in insn.args:
                    if reg != a.defi.reg:
                        break
                else:
                    return None

            preds = ["&&%s" % p.label for p in bb.preds]
            vals = [str_arg(a) for a in insn.args]
            args = []
            for t in zip(preds, vals):
                args.extend(t)
            args.append("NULL")
            rhs = "%s(%s)" % ("phi", ", ".join(args))
        elif insn.op[0].isalpha() or insn.op.startswith("@"):
            op = insn.op
            args = insn.args
            if insn.op == "call":
                op = args[0]
                args = args[1:]
            rhs = "%s(%s)" % (op, ", ".join([str_arg(a) for a in args]))
        else:
            if insn.op == "=":
                rhs = str_arg(insn.args[0])
            else:
                assert len(insn.args) == 2
                rhs = "%s %s %s" % (str_arg(insn.args[0]), insn.op, str_arg(insn.args[1]))


        if not insn.dest:
            res = "%s" % rhs
        else:
            if use_regs:
                dest = insn.reg
            else:
                dest = insn.dest_name(cfg.is_ssa)
            res = "%s = %s" % (dest, rhs)
        return prefix + res

    return render(insn)


def get_local_vars(cfg, use_regs):
    vars = set()
    for bb in cfg.bblocks:
        for insn in bb.insns:
            if insn.dest:
                if use_regs:
                    vars.add(insn.reg)
                else:
                    if cfg.is_ssa:
                        vars.add(insn.dest_name())
                    else:
                        if insn.dest not in cfg.params:
                            vars.add(insn.dest)
    return sorted(vars)


def is_str_data(data):
    # Whether Data is a simple string.
    return len(data.desc) == 1 and data.desc[0][0] == "str"


def render_data(data, file=None):
    if is_str_data(data):
        print("char %s[%d] = %s;" % (data.name, len(data.desc[0][2]), data.desc[0][1]), file=file)
    else:
        assert False


def render_cfg(func, use_regs=False, file=None):
    config.SSA_SUFFIX_CHAR = "_"

    print("int %s(%s) {" % (func.name, ", ".join(["int %s" % p for p in func.params])), file=file)

    if func.is_ssa:
        print("    SSA_HEADER();", file=file)

    local_vars = get_local_vars(func, use_regs)
    if local_vars:
        print("    long %s;" % ", ".join(local_vars), file=file)

    for i, bb in enumerate(func.bblocks):
        next_bb = func.bblocks[i + 1] if i < len(func.bblocks) - 1 else None
        label = "L(%s):" % bb.label if func.is_ssa else "%s:" % bb.label
        print(label, file=file)
        for insn in bb.insns:
            insn_str = render_insn(insn, bb, func, use_regs)
            if insn_str is None:
                continue
            print("    " + insn_str + ";", file=file)
        if len(bb.succs) == 1 and bb.succs[0] is not next_bb:
            print("    goto %s;" % bb.succs[0].label, file=file)
    print("}", file=file)


def render_item(el, use_regs=False, file=None):
    if isinstance(el, Func):
        render_cfg(el, use_regs, file)
    elif isinstance(el, Data):
        render_data(el, file)
    else:
        assert False


def render_module(mod, use_regs=False, file=None):
    print('#include "pseudoc.h"\n', file=file)
    need_empty_line = False
    for el in mod.contents:
        if need_empty_line:
            print(file=file)
        render_item(el, use_regs, file)
        need_empty_line = True

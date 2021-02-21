import sys
import logging
import argparse
import re

from lexer import Lexer
from pseudoc import config
from pseudoc import parser


log = logging.getLogger(__name__)


PASS_NAME = re.compile(r"[A-Za-z_0-9.]+")
PARAM_NAME = re.compile(r"[A-Za-z_][A-Za-z_0-9.]*")
PARAM_VALUE = re.compile(r"[^,()]+")

def parse_passes_spec(s, pass_list):
    lex = Lexer(s)
    while not lex.eol():
        name = lex.expect_re(PASS_NAME, err="expected pass name ([dotted] identifier)")
        mod = None
        if "." in name:
            mod, name = name.rsplit(".", 1)
            mod = __import__(mod)
        passfunc = getattr(mod, name)
        params = {}
        if lex.match("("):
            while not lex.match(")"):
                k = lex.expect_re(PARAM_NAME, err="expected pass param name")
                v = True
                if lex.match("="):
                    v = lex.expect_re(PARAM_NAME, err="expected pass param name")
                    v = {"True": True, "False": False}.get(v, v)
                params[k] = v
                lex.match(",")
        passes_list.append((passfunc, params))
        lex.match(",")


argp = argparse.ArgumentParser(description="Parse PseudoC program and apply transformations")
argp.add_argument("file")
argp.add_argument("-o", "--out", help="Output to file")
argp.add_argument("-x", "--xforms", default=[], action="append", help="transformation(s) to apply")
args = argp.parse_args()

passes_list = []

for x in args.xforms:
    parse_passes_spec(x, passes_list)


def __main__():
    with open(args.file) as f:
        mod = parser.parse(f)

    # Set up outfile before starting processing, as some passes may output
    # additional information there prior to processed program.
    outfile = None
    if args.out:
        outfile = open(args.out, "w")

    need_empty_line = False
    for func in mod.contents:
        if need_empty_line:
            print(file=outfile)

        for pass_func, pass_params in passes_list:
            pass_func(func, **pass_params)

        func.dump(file=outfile)

        need_empty_line = True

    if outfile:
        outfile.close()


if __name__ == "__main__":
    __main__()

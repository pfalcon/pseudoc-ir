# PseudoC IR

PseudoC is a program representation Intermediate Language (IL) with familiar
C-like syntax, suitable for program analysis, compiler optimization, machine
code generation, etc. tasks. It is also an Intermediate Representation (IR)
of this language (i.e. implementations of data structures), on which various
program analysis and optimization algorithms can be coded.

Following are the main differences of PseudoC from other ILs/IRs:

* The main goal of PseudoC is simplicity. Simplicity of learning,
  simplicity of the main PseudoC code, simplicity of algorithm
  implementations.
* Familiar C-like syntax (PseudoC is effectively a platform-independent
  assembler with C syntax).
* Flexibility and support for different features. For example, it's
  suitable to represent both non-SSA and SSA code, can represent typed
  and untyped code, can represent high-level aggregate data access, etc.
* Interoperable: includes tools to convert LLVM IR to PseudoC and
  PseudoC to C.

This project is intended to be reincarnation of the ideas in
https://github.com/pfalcon/ScratchABlock/blob/master/docs/PseudoC-spec.md,
but defined in more generic and formal fashion (and with applicability to
code generation, e.g. JITting).

This is WIP and done in "incremental elaboration" fashion, similar to
workflow of https://github.com/rui314/chibicc#contributing , so the
repository is rebased.

# Credits and licensing

This project is Copyright (c) 2020-2021 by Paul Sokolovsky and provided
under the terms of MIT license.


MiniD Interface Compiler
========================

This program exists to make it a little less tedious to write MiniD bindings
for D code.

It uses an interface description language that is vaguely MiniD-ish (it was
designed not ease of parsing more than anything) which the compiler will then
translate into D code.

This project is still in its early stages, although lexing, parsing and
semantic analysis is broadly complete.

Still To Do
===========

- Finish codegen.
- Support packages (either using package files, or just looking at
  directories).
- Write D-side binding library.
- Write actual user frontend.


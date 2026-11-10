"""monomorph (DavidBuchanan314) - the ELF loader, dynamically linked.

The last open item on mcrit-data issue #20, and the one this corpus had
previously investigated and declined. The reason it was declined was never
that the project is small; it was that the only way anyone had built it put
somebody else's code under its name. That is fixable, so it is built here.

**Four functions, and that is the whole project.** ``loader/monomorph.c`` is
96 lines: ``get_bit``, ``decode_buf`` and ``inflate_buf`` are ``static``, and
``main`` is the entry point. Nothing else in the repository compiles - the
rest is Python tooling for generating MD5 collision blocks. Under the floor
this corpus applies by default it would be refused; it is recorded because
four real functions are four more than nothing, and ``min_functions`` exists
for a project that genuinely contains that few.

**Why it is not built the way upstream builds it.** ``loader/Makefile`` says

    gcc monomorph.c -o monomorph -static -Wall -Wextra -std=c99 -lz

and ``-static`` is exactly the problem ``scripts/corpus/README.md`` recorded:
the artefact then carries 1397 function symbols of which 1393 are glibc and
zlib, there is no glibc baseline in this corpus to subtract them with, and
they would enter under monomorph's name and duplicate ``data/libzlib``.
Dropping ``-static`` leaves glibc and zlib imported instead of absorbed, and
what remains is the four functions above plus the ELF start glue the measured
Linux baseline drops. Everything else about the build is upstream's own.

**What that means for a real sighting, stated rather than glossed.** Upstream
ships ``bin/monomorph.linux.x86-64.benign`` and it *is* statically linked -
2001 symbols in the shipped binary - so a copy met in the wild will carry
glibc and zlib alongside these four functions. This artefact does not model
that, deliberately: the four bodies here are the ones that identify monomorph,
and they match in a static binary just as well, while the glibc and zlib
bodies around them are not this project's and are better recognised as what
they are. zlib already has a family here.

x86-64 only. The project is about x86-64 ELF: what makes it distinctive is a
4 MB array of MD5 collision blocks that it decodes and inflates over itself,
and both the shipped binary and the README are that architecture. The
technique also is not really code - upstream points at a collision detector
for identifying it - so the reference value here is the loader around it, not
the trick.

No optimisation flag, because upstream passes none and the binary upstream
ships is the one people meet. This is the opposite call to minhook.py's, which
adds ``-O2`` because a vendored source copy is compiled with the consumer's
flags; monomorph is distributed as a binary, so upstream's own flags are the
shape in the wild.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Upstream's command with -static removed and nothing else changed. -lz still
# links zlib, as a shared library now, so inflate_buf calls into it rather
# than carrying it.
_BUILD = ("{cc} {archflag} monomorph.c -o monomorph -Wall -Wextra -std=c99 -lz")


RECIPES = {
    "monomorph_2022-09-30": Recipe(
        family="monomorph",
        version="2022-09-30",
        upstream="https://github.com/DavidBuchanan314/monomorph",
        license="MIT",
        source=Source(
            git_url="https://github.com/DavidBuchanan314/monomorph.git",
            git_ref="846722239689de87eb5140ed7984099c3056e262"),
        build=[BuildStep(_BUILD, cwd="loader")],
        artifacts=[Artifact(path="loader/monomorph",
                            component="monomorph")],
        toolchains=["linux_x64"],
        # Four functions is the project, not a build accident; see the module
        # docstring.
        min_functions=1,
        build_flags="-Wall -Wextra -std=c99 -lz, no optimisation flag "
                    "(upstream's own command), with upstream's -static "
                    "removed so glibc and zlib are imported rather than "
                    "linked in",
        notes="The loader from loader/monomorph.c, which is the only thing in "
              "the repository that compiles; the rest is Python tooling for "
              "generating MD5 collision blocks. Four functions and that is the "
              "whole project: get_bit, decode_buf and inflate_buf are static, "
              "main is the entry point. Built without upstream's -static, "
              "because a static link put 1397 function symbols in the image of "
              "which 1393 were glibc and zlib - no glibc baseline exists here "
              "to subtract them and they would have entered under this name "
              "and duplicated data/libzlib. Upstream does ship a statically "
              "linked binary, so a copy met in the wild carries glibc and zlib "
              "around these four bodies; the four still match. x86-64 only, "
              "which is what upstream ships and what the technique is written "
              "for. What actually distinguishes the project is a 4 MB array of "
              "MD5 collision blocks, which is data rather than code, so "
              "upstream's own advice is to identify it with a collision "
              "detector; the reference value here is the loader around it.",
    ),
}

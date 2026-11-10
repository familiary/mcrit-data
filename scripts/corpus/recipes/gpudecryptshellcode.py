"""eversinc33/GpuDecryptShellcode - shellcode decrypted on the GPU via OpenCL.

The proof of concept behind the OpenCL-GPU-malware write-ups: the payload is
XORed on the GPU by an OpenCL kernel rather than on the CPU, so a memory
scanner watching the host process never sees the decryption loop.

**Two functions, and they are the whole project**: ``getErrorString`` and
``main``, in one 193-line translation unit. ``min_functions`` is 2.

This family's reference value is the weakest in the corpus, and the recipe
says so rather than leaving a reader to discover it. Three separate reasons,
none of which is the function count:

**The technique is not native code at all.** What makes this project
interesting is the GPU-side decryption, and that is a C string literal -
``"__kernel void decrypt(__global char* encrypted, ...)"`` on line 11 -
handed to ``clCreateProgramWithSource`` and compiled by the GPU driver at run
time. It never becomes x86 instructions and cannot appear in any artefact
this pipeline produces. What is recorded is the host-side plumbing that sets
up a buffer and enqueues a kernel.

**One of the two functions is not really this project's.** ``getErrorString``
is a 64-case switch mapping OpenCL error codes to their string names, and it
is the ubiquitous copy-pasted helper - the ``// run-time and JIT compiler
errors`` comment above the first case is verbatim from the version circulated
in gists and answers for a decade. It is in the artefact because it is in the
binary, but a match on it says "somebody used OpenCL and pasted the usual
error table", not "this is GpuDecryptShellcode". It is also the obvious
candidate to collide with any future OpenCL family here, and that collision
would be a true positive about the snippet and a false one about the project.

**What is left is ``main``.** Which is the OpenCL host boilerplate: enumerate
platforms, pick a device, build the program, set three kernel arguments,
enqueue, read back.

Recorded anyway, because the corpus's floor is not the only thing that
decides what is worth having and a maintainer asked for it - but recorded with
the above stated, so nobody reads a hit on this family as more than it is.

Built with MinGW rather than MSVC despite upstream shipping only a .sln and
.vcxproj, and that is a smaller deviation here than it was for Cronos: the
project file hardcodes one developer's absolute paths
(``C:\\Users\\jdoe\\source\\OpenCL-CLHPP\\include``,
``C:\\Users\\jdoe\\source\\OpenCL-Headers``) and
``$(INTELOCLSDKROOT)\\lib\\x64``, none of which exists on any runner, so the
MSVC route needs its include and library paths replaced wholesale before it
builds anywhere at all. Either compiler therefore needs the headers supplied
externally, which is what ``extra_sources`` does below.

Linked with ``-shared-libgcc`` and *without* ``-static-libstdc++``, which
matters more here than in most recipes: this is a C++ translation unit that
uses ``<iostream>``, ``<string>`` and ``<fstream>``, and a static libstdc++
link pulls roughly thirteen thousand libstdc++ and libgcc functions into the
image, all of which would be attributed to this two-function family. The
corpus README records that trap; nlohmann.py makes the same choice for the
same reason.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The OpenCL headers, pinned. CLHPP is the C++ binding
# (<CL/opencl.hpp>) and OpenCL-Headers supplies the C headers it includes;
# both are needed and neither is vendored into the project. Pinned to the same
# dated tag so the pair is coherent - CLHPP tracks the C headers' releases and
# mixing a new binding with old C headers is its own class of build failure.
_CLHPP = Source(git_url="https://github.com/KhronosGroup/OpenCL-CLHPP.git",
                git_ref="v2026.05.29")
_HEADERS = Source(git_url="https://github.com/KhronosGroup/OpenCL-Headers.git",
                  git_ref="v2026.05.29")

# The import library for the system OpenCL.dll. See
# scripts/corpus/exercisers/opencl_import.def for why it is a .def and a
# dlltool call rather than the real OpenCL-ICD-Loader: linking the loader's
# static library would file its several hundred functions under this family.
_IMPLIB = ('{prefix}dlltool '
           '-d {repo}/scripts/corpus/exercisers/opencl_import.def '
           '-l libOpenCL.a')

# -O2 rather than upstream's Release default, which is also /O2 - this is the
# one flag choice here that needs no argument.
#
# CL_HPP_TARGET_OPENCL_VERSION is stated rather than left to the header's
# default: CLHPP warns and picks a version when it is unset, and 300 is what
# the pinned C headers are. CL_HPP_ENABLE_EXCEPTIONS is deliberately NOT set,
# because upstream does not set it and the code checks cl_int return codes by
# hand - turning it on would change which bodies the header instantiates.
#
# -shared-libgcc and no -static-libstdc++; see the docstring.
_BUILD = ('{cxx} GpuDecryptShellcode.cpp -o GpuDecryptShellcode.exe '
          '-O2 -std=c++17 -DCL_HPP_TARGET_OPENCL_VERSION=300 '
          '-I{opencl_headers} -I{opencl_clhpp}/include '
          '-L. -lOpenCL -shared-libgcc')

_FLAGS = ("-O2 -std=c++17 -DCL_HPP_TARGET_OPENCL_VERSION=300 against pinned "
          "OpenCL-Headers and OpenCL-CLHPP v2026.05.29, linked -shared-libgcc "
          "against an import library dlltool generates from "
          "scripts/corpus/exercisers/opencl_import.def for the system "
          "OpenCL.dll. Not -static-libstdc++, which would pull ~13,500 "
          "libstdc++ and libgcc bodies into a two-function family")


RECIPES = {
    # No tags in the repository, so pinned by full commit and versioned by its
    # date. HEAD is 6ce1ba2b8384de6a090193b3ba18dd5b81fe1fe1, 2025-05-22.
    "GpuDecryptShellcode_2025-05-22": Recipe(
        family="GpuDecryptShellcode",
        version="2025-05-22",
        upstream="https://github.com/eversinc33/GpuDecryptShellcode",
        # No LICENSE or COPYING file and no copyright or licence line in the
        # single source file, the project files or the README. "none" is the
        # fact and is copied verbatim into provenance.json, as
        # callobfuscator.py, ekko.py and foliage.py all record for the same
        # situation.
        license="none",
        source=Source(
            git_url="https://github.com/eversinc33/GpuDecryptShellcode.git",
            git_ref="6ce1ba2b8384de6a090193b3ba18dd5b81fe1fe1"),
        extra_sources={"opencl_clhpp": _CLHPP, "opencl_headers": _HEADERS},
        build=[BuildStep(_IMPLIB), BuildStep(_BUILD)],
        artifacts=[
            Artifact(path="GpuDecryptShellcode.exe",
                     component="GpuDecryptShellcode.exe"),
            # is_library stays true, as it is for every executable in this
            # corpus; validate.py requires it.
        ],
        toolchains=["mingw_x64"],
        # Two, measured, and the whole project: getErrorString and main. See
        # Recipe.min_functions. Read the docstring before treating this as
        # two functions' worth of reference data - one of them is a
        # copy-pasted OpenCL error table and the technique the project is
        # known for is a runtime-compiled GPU kernel that is never native
        # code.
        min_functions=2,
        build_flags=_FLAGS,
        notes="Shellcode decrypted on the GPU by an OpenCL kernel, so a "
              "memory scanner never sees the decryption loop on the host. Two "
              "functions are the whole project - getErrorString and main, in "
              "one 193-line translation unit - so min_functions=2. This is "
              "the weakest reference data in the corpus and the recipe says "
              "so for three reasons that are not the count. The technique is "
              "not native code: the GPU kernel is a C string literal handed "
              "to clCreateProgramWithSource and compiled by the driver at run "
              "time, so it can never appear in any artefact this pipeline "
              "produces, and what is recorded is the host-side plumbing. One "
              "of the two functions is not really this project's: "
              "getErrorString is a 64-case OpenCL error-code-to-string "
              "switch, the ubiquitous copy-pasted helper - the '// run-time "
              "and JIT compiler errors' comment is verbatim from the version "
              "circulated for a decade - so a match on it means somebody used "
              "OpenCL and pasted the usual table, not that this project is "
              "present, and it is the obvious candidate to collide with any "
              "future OpenCL family here. What remains is main, which is "
              "OpenCL host boilerplate. Built with MinGW although upstream "
              "ships only a .sln: the project file hardcodes one developer's "
              "absolute include paths and $(INTELOCLSDKROOT), so the MSVC "
              "route needs its paths replaced before it builds anywhere "
              "either, and both compilers need the Khronos headers supplied "
              "externally - they are pinned here as extra_sources at "
              "v2026.05.29. mingw-w64 ships no OpenCL import library, so one "
              "is generated with dlltool from "
              "scripts/corpus/exercisers/opencl_import.def, listing exactly "
              "the 21 entry points the program references; the real "
              "OpenCL-ICD-Loader is deliberately not linked because its "
              "static library would file several hundred of its own functions "
              "under this family. Linked -shared-libgcc and NOT "
              "-static-libstdc++, which would pull roughly 13,500 libstdc++ "
              "and libgcc bodies into a two-function family. No licence of "
              "any kind. Nothing in the tree is prebuilt.",
    ),
}

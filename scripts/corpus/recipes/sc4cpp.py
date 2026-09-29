"""sc4cpp - a C++ shellcode framework (mcrit-data issue #14).

Previously on the "investigated but not built" list, for a reason that was
true when it was written and is not any more: "upstream repository and the
owning GitHub account are both gone (404)". Both are still gone. The source
is no longer lost.

**Where the source comes from, and why its bytes can be trusted.** Software
Heritage crawled ``https://github.com/windpiaoxue/sc4cpp`` once, on
2023-07-13, and the visit came back ``full``. That visit is snapshot
``e5e82503dcaf40a924c035289ff15cda663f7ab9``, whose single branch
``refs/heads/master`` points at revision
``e252d9a55228303f3a8565b6a347c6d386dbb5d3`` - "Fixed bugs and added a test
tool", authored 2021-08-29 - whose root tree is directory
``d469e55b226b153ab9c380c8783ed78621b45b2d``. The recipe pins the vault's
flat tarball of that directory.

What makes this different from an ordinary web archive is that Software
Heritage stores *git objects*, not rendered pages. A git blob id is the
SHA-1 of the content with its header, and a tree id is built from its
entries' ids, so the directory id above is a hash over the whole tree: any
byte that differed anywhere under it would give a different directory id,
and the id is the thing this recipe names. All 18 files were checked
individually against that - blob id, length and SHA-256 - before the recipe
was written, and all 18 match. The tarball digest pinned below was fetched
twice, minutes apart, and came back identical both times, so the vault
cooker is deterministic enough to pin.

The Wayback Machine holds a snapshot of the repository page at
``20250405130748``, and it is *not* part of this record: web.archive.org is
not reachable from the machine this was built on (the egress proxy refuses
it), so nothing was cross-checked against it and nothing here rests on it.
The tree-hash argument above does not need a second source; it is what a
git fetch from the live repository would have verified too.

**Licence: MIT**, ``LICENSE`` in the tree, "Copyright (c) 2021 windpiaoxue",
21 lines. ``include/sc4cpp.h`` repeats the grant in its own header comment
under the author's other name, "smh <windpiaoxue@foxmail.com>". So the
licence objection that keeps BlackLotus and the SysWhispers2 x86 stubs off
this list does not apply here.

**What the project is.** A framework for writing position-independent
Windows shellcode as ordinary C++. ``SC_MAIN_BEGIN``/``SC_MAIN_END`` wrap
the user's entry point in exported ``SCBegin`` and ``SCEnd`` markers;
``__declspec(code_seg(".code$..."))`` sorts the emitted functions into one
contiguous run between them; ``SC_IMPORT_API_BATCH`` resolves imports at
runtime by walking the PEB loader list and comparing FNV-1a hashes of module
and export names; ``SC_PISTRINGA``/``SC_PISTRINGW`` build string literals on
the stack so nothing lands in ``.rdata``. ``src/scextractor.py`` then reads
the built PE with pefile and writes out the bytes between the two markers.

**What is recordable, and what is not.**

``include/sc4cpp.h`` is 9,777 bytes of macros and ``SC_FORCEINLINE``
templates. It has no compiled body of its own and never will: every one of
its functions is force-inlined into whatever calls it, so there is nothing
to disassemble until somebody writes a program with it. The only thing in
the repository that compiles to code is ``src/sc4cpp.cpp``, 1,064 bytes,
which is the worked example from the README - a MessageBox demo. That is
what this recipe builds, and calling it "sc4cpp" needs justifying rather
than assuming.

It is justified by measurement. Compile a translation unit that does
nothing at all - resolve ``ExitProcess`` through the batch macros and call
it - and its ``SCMain`` is already 161 instructions on x64. The example's
``SCMain`` is 213. So 76% of what this artefact records is the framework's
macro expansion: the PEB walk, the two FNV-1a loops, the
``LoadLibraryA``/``GetProcAddress`` pair every batch begins with. That
block is in every program anyone writes with this header, and it is what an
analyst actually meets. The MessageBox calls around it are the part that is
only the example's.

**What that buys, stated as what it is rather than as what would sound
better.** It is a *fuzzy* match, not an exact one, and the difference
matters enough to measure. Everything in the header is ``SC_FORCEINLINE``,
so the framework block is inlined into ``SCMain`` together with whatever the
user wrote and the two become one function body: two different sc4cpp
programs do **not** share a ``SCMain`` PicHash. Compiling an unrelated
program with this header - open a file, exit - and comparing against this
artefact:

* exact PicHash matches: the 3-instruction ``SCBegin``, ``SCEnd`` and the
  ``ret`` after it, and nothing else;
* minhash agreement between the two ``SCMain`` bodies: **59%**, and 63%
  between that program's ``SCMain`` and this artefact's ``WorkerThread``.

Which is to say this family is worth having for MCRIT's fuzzy similarity and
is close to worthless for exact matching, and a report that comes back at
that score is saying "written with sc4cpp", not "is this program". That is
the useful claim for a framework: nothing about sc4cpp is distributed as a
binary, so there is no fixed body to match exactly in the first place.

**The prebuilt files in ``test/`` are not recorded.** ``msgbox_x86.sc`` and
``msgbox_x64.sc`` are upstream's own build of this same example, and
``runsc_x86.exe``/``runsc_x64.exe`` are a 28-line loader that VirtualAllocs a
file and calls it. The house position on upstream-committed binaries is
donut.py's and srdi.py's and pe_to_shellcode.py's - record them, because
those exact bytes are what ships - and it does not reach these. Two reasons,
and the first is decisive on its own:

* ``Recipe.slug`` labels every ``is_blob`` artefact ``msvc``, deliberately,
  because the three recipes that route exists for all extract MSVC output.
  These blobs are not MSVC output. Upstream's README names "Clang for
  Windows" and its flags are clang-cl's, so a ``sc4cpp_..._msvc_x86_...``
  filename would state something false about the compiler, in the one place
  a reader cannot see a note contradicting it. Fixing that means changing
  how every blob in the corpus is named, which is not this recipe's to do.
* They are a test fixture, not a shipped artefact. donut's loader blobs are
  embedded in every payload donut generates and sRDI's is what the PyPI
  package emits; nothing sc4cpp produces carries ``msgbox_x64.sc``. What a
  sample built with sc4cpp shares with these files is the framework block,
  and this recipe records that from source with symbols on it.

``runsc`` is source-available (``test/runsc/runsc.cpp``) and would build,
and is still not recorded: it is one ``main`` that reads a file and jumps to
it, it is a debugging aid rather than part of the framework, and at one
function it is below anything worth a minhash. ``src/scextractor.py`` is
Python; this pipeline records compiled code.

**Why clang against mingw-w64 and not clang-cl.** The header opens with

    #if !defined(__clang__) || !defined(_WIN32)
    #error "sc4cpp only supports Clang on windows"

so GCC is out by upstream's own declaration, and what follows -
``__declspec(code_seg)``, ``__declspec(naked)`` with MSVC ``__asm`` blocks
and ``__asm _emit`` - has no GCC equivalent anyway. clang-cl proper was
tried first and cannot work here: ``clang-cl --target=x86_64-pc-windows-msvc``
compiles a freestanding translation unit fine, but on anything including a
Windows header it stops at

    fatal error: 'Windows.h' file not found

because a ``*-pc-windows-msvc`` target needs the Windows SDK and the MSVC
STL, and neither is on a Linux runner. So the target is
``*-w64-windows-gnu``: clang's code generator, mingw-w64's headers, import
libraries and linker. ``__clang__`` and ``_WIN32`` are both defined there,
so upstream's guard passes as written.

**The three obstacles, and the command-line settings that answer them.**
Nothing under the source tree is touched.

1. ``fatal error: 'Windows.h' file not found``. mingw-w64 ships
   ``windows.h``; the header asks for ``Windows.h``, which resolves only on
   a case-insensitive filesystem. The first build step writes a one-line
   forwarding header ``Windows.h`` containing ``#include <windows.h>`` into
   the artefact directory - *outside* the source tree - and puts that
   directory first on the include path. Being first is what makes it work
   and not recurse: the sysroot has no ``windows.h`` in the shim directory,
   so the inner include falls through to mingw-w64's. A symlink to the
   sysroot's absolute path was the first attempt and is worse - it builds,
   but it hardcodes ``/usr/x86_64-w64-mingw32/include`` and it trips
   ``-Wnonportable-include-path`` on every build.

2. ``error: no member named 'index_sequence' in namespace 'std'``, and the
   same for ``make_index_sequence``, from the ``PIString`` template.
   ``sc4cpp.h`` includes ``<type_traits>`` and nothing else from the
   standard library; MSVC's ``<type_traits>`` drags in the index-sequence
   machinery and libstdc++'s does not. ``-include utility`` supplies it
   ahead of the translation unit. This is a difference between two standard
   libraries, not a defect in either, and ``-include`` is the setting that
   exists for it.

3. ``warning: unknown attribute 'code_seg' ignored [-Wunknown-attributes]``.
   A warning rather than an error, and the most expensive of the three: with
   ``code_seg`` ignored the four ``.code$`` sections never appear, the
   emitted functions land in ``.text`` in whatever order the compiler likes,
   and ``SCBegin``..``SCEnd`` stops being a contiguous run - which is the
   entire mechanism of the project. ``-fms-extensions`` turns the attribute
   on; ``-fasm-blocks`` does the same for the x86 ``__asm``/``_emit``
   thunk in ``SC_BEGIN_CODE``. With both, the x64 object comes out carrying
   ``.code$CAA``, ``.code$CBA``, ``.code$CXI`` and ``.code$CZZ``, and the
   linker merges them into one ``.code`` section in that order.

**Upstream's flags, and precisely what differs.** The README gives
``/O2 /Os /MT /GS- /Gs1048576 -mno-sse`` and the ``.vcxproj`` adds
``/ENTRY:SCBegin``, ``/SUBSYSTEM:WINDOWS``, ``ExceptionHandling false`` and
``FunctionLevelLinking``. Under the GNU driver those are ``-Os`` (clang-cl
maps ``/O2`` to ``-O2`` and ``/Os`` to ``-Os``, and the later wins),
``-fno-stack-protector``, ``-mstack-probe-size=1048576``, ``-mno-sse``,
``-fno-exceptions``, ``-ffunction-sections``, ``-Wl,-e,SCBegin`` and
``-Wl,--subsystem,windows``. Two things are genuinely different and neither
is silent:

* ``/MT`` has no counterpart and needs none. It selects the static MSVC CRT,
  and this image has no C runtime in it at all: the entry point is
  ``SCBegin``, the link is ``-nostdlib``, and the built PE has an empty
  import directory and calls nothing outside itself. Checked rather than
  assumed - no ``__chkstk`` reference in either architecture, which is also
  what confirms ``-mstack-probe-size`` took.
* The ABI is mingw-w64's, not MSVC's. For this translation unit that means
  Itanium name mangling on the one non-``extern "C"`` function
  (``_Z12WorkerThreadPv`` rather than ``?WorkerThread@@...``) and a
  different C++ runtime that nothing here calls. It does not reach the code
  generator: the calling convention, the register allocator and the
  instruction selection are clang's either way.

``-Wl,--no-insert-timestamp`` is this recipe's ``/Brepro``, and it is not
optional. Without it two builds of the same source minutes apart differ in
two bytes - the COFF header's TimeDateStamp and the export directory's -
and the recorded sha256 that all of this provenance rests on would be a
different number every run. With it they are byte-identical, which was
checked by building twice rather than assumed.

**How close that lands, measured against upstream's own build.** This is
the check that decides whether the substitution is honest, so it was run
rather than argued. Upstream's committed ``msgbox_x86.sc`` is 1619 bytes;
``SCEnd - SCBegin`` in this recipe's x86 image is 1619 bytes, with ``SCMain``
at +0x1c and ``WorkerThread`` at +0x33f in both. On x64 the first function
is a PicHash match - ``1a5f4ffb4d0919a6`` in this build and in upstream's
blob, the same three instructions - and the other two are 213 and 217
instructions against upstream's 219 and 219. So: same layout, same size,
same shape, and the bodies differ in register allocation, which is what four
years of clang releases between upstream's compiler and clang 18 look like.
Not byte-identical, and this docstring does not claim it is; a recipe cannot
pin a compiler upstream never named a version for.

**Function counts.** x64: 5 functions, 435 instructions. x86: 9 functions,
519 instructions. Every one of them is this build's own code - no import
thunks (there are no imports; that is the project's point), no CRT or STL
(``-nostdlib``), nothing vendored. The named four are ``SCBegin``,
``SCMain``, ``WorkerThread`` and ``SCEnd``; the rest are SMDA splitting a
block at an ``int3``, which is the inlined ``__debugbreak()`` on
``GetProcAddressByHash``'s not-found path and the one ``SCEnd`` itself is.
The symbol check sees 3 of 3 above its instruction floor on both.

``min_functions=4`` because four is what the project has - the two markers
and the two functions the example defines - and the default floor of eight
would refuse it. It is set to what the source contains, not to what the
build happened to produce: both artefacts in fact report more than four, and
the number is deliberately the smaller, honest one. Same call as
monomorph.py's, for the same reason.

``drop_crt_glue=False``: there is no compiler runtime in these images to
drop. Measured, not assumed - the import directory is empty, nothing outside
``.code`` is reached, and running the filter would only cost a baseline
measurement of probe DLLs that have nothing to do with this build.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Written into the artefact directory, never into the source tree. See
# obstacle 1 in the module docstring for why a forwarding header beats a
# symlink here.
_SHIM = ("mkdir -p {out}/sc4cpp-caseshim && "
         "printf '#include <windows.h>\\n' > {out}/sc4cpp-caseshim/Windows.h")

# Upstream's /O2 /Os /MT /GS- /Gs1048576 -mno-sse and its project file's
# ExceptionHandling/FunctionLevelLinking, in the GNU driver's spelling, plus
# the three settings that make the source compile at all.
_FLAGS = ("-std=c++17 -fms-extensions -fasm-blocks -include utility "
          "-Os -fno-stack-protector -mstack-probe-size=1048576 -mno-sse "
          "-fno-exceptions -ffunction-sections")

# The entry symbol carries a leading underscore on 32-bit PE and does not on
# 64-bit, and no placeholder spells that difference; without the right one ld
# says "cannot find entry symbol SCBegin; defaulting to 00401000" and the
# image no longer starts where upstream's /ENTRY:SCBegin puts it. A POSIX
# shell is safe to assume because clang_x86/clang_x64 register only where the
# mingw-w64 sysroot is, which is a Linux checkout.
_BUILD = ("E=SCBegin; [ {bitness} -eq 32 ] && E=_SCBegin; "
          "{cxx} {archflag} " + _FLAGS + " "
          "-Iinclude -I{out}/sc4cpp-caseshim src/sc4cpp.cpp "
          "-nostdlib -Wl,-e,$E -Wl,--subsystem,windows "
          "-Wl,--no-insert-timestamp "
          "-o sc4cpp_{arch}.exe")


RECIPES = {
    # The one revision Software Heritage holds, dated by its author date.
    # There are no tags; the repository is gone and there will not be more.
    "sc4cpp_2021-08-29": Recipe(
        family="sc4cpp",
        version="2021-08-29",
        upstream="https://github.com/windpiaoxue/sc4cpp (deleted; recovered "
                 "from Software Heritage snapshot "
                 "e5e82503dcaf40a924c035289ff15cda663f7ab9, revision "
                 "e252d9a55228303f3a8565b6a347c6d386dbb5d3, directory "
                 "d469e55b226b153ab9c380c8783ed78621b45b2d)",
        license="MIT",
        source=Source(
            url="https://archive.softwareheritage.org/api/1/vault/flat/"
                "swh:1:dir:d469e55b226b153ab9c380c8783ed78621b45b2d/raw",
            sha256="f4b0e8ab911e7853835b17e16a751d70cc489eb9eb461f4ba79087c574f47b80"),
        build=[BuildStep(_SHIM), BuildStep(_BUILD)],
        # is_library stays true although this is an EXE: the flag marks a
        # sample as reference material rather than malware, which is what
        # MCRIT keys its library views off, and validate fails a false here.
        artifacts=[Artifact(path="sc4cpp_{arch}.exe", component="example")],
        toolchains=["clang_x86", "clang_x64"],
        # Four: SCBegin, SCMain, WorkerThread, SCEnd. See the docstring.
        min_functions=4,
        # -nostdlib; there is no compiler runtime in the image to filter.
        drop_crt_glue=False,
        build_flags="-Os -fno-stack-protector -mstack-probe-size=1048576 "
                    "-mno-sse -fno-exceptions -ffunction-sections "
                    "-std=c++17 -fms-extensions -fasm-blocks -include utility, "
                    "linked -nostdlib --no-insert-timestamp with upstream's "
                    "/ENTRY:SCBegin and "
                    "/SUBSYSTEM:WINDOWS; upstream's own /O2 /Os /MT /GS- "
                    "/Gs1048576 -mno-sse in the GNU driver's spelling, built "
                    "by clang against the mingw-w64 sysroot rather than by "
                    "clang-cl against the MSVC one",
        notes="The example translation unit src/sc4cpp.cpp, which is the only "
              "thing in the repository that compiles to code: include/sc4cpp.h "
              "is macros and force-inlined templates and has no body of its "
              "own. 76% of the recorded SCMain is framework macro expansion "
              "rather than the example - a translation unit that resolves one "
              "API and calls it already yields 161 of these 213 instructions - "
              "so what matches here is the PEB walk, the FNV-1a module and "
              "export hash loops and the LoadLibraryA/GetProcAddress pair that "
              "every program written with this header contains. That is a "
              "fuzzy match and not an exact one: the header is entirely "
              "force-inlined, so the framework block and the user's code "
              "become one body and two different sc4cpp programs share no "
              "SCMain PicHash. Measured against an unrelated program built "
              "with the same header, the only exact matches are the "
              "3-instruction SCBegin and the two one-instruction markers, "
              "while the SCMain bodies agree on 59% of their minhash. This "
              "family identifies the framework, not a program. Built with "
              "clang targeting mingw-w64, not clang-cl: upstream's header "
              "refuses to compile under anything but clang, and a "
              "*-pc-windows-msvc target needs a Windows SDK a Linux runner "
              "does not have. Against upstream's own committed build the x86 "
              "image is the same 1619 bytes with SCMain and WorkerThread at "
              "the same offsets, and the x64 SCBegin is a PicHash match; the "
              "two large bodies differ in register allocation, being a much "
              "later clang. The prebuilt test/*.sc blobs and runsc_*.exe are "
              "not recorded - Recipe.slug would label a blob msvc and these "
              "are clang-cl output, and they are a test fixture rather than "
              "anything sc4cpp ships. Source recovered from Software Heritage; "
              "the upstream repository and its owning account are both 404.",
    ),
}

"""libgcc.a and libgcc_eh.a of the prebuilt GCC 13 toolchains of this host.

Backlog issue #4 asks for the GCC compiler runtime as a family of its own,
harvested from prebuilt toolchains instead of built. libgcc_harvest.py holds
the old pins (GCC 4.1.2 from uClibc.org mini-native, GCC 4.2.1 from Aboriginal
Linux 1.4.4); this module is the two pins the issue names for the toolchains
of this corpus:

  * gcc13_x64: the Ubuntu 24.04 GCC 13.3.0 (13.3.0-6ubuntu2~24.04.1) libgcc.a
    and libgcc_eh.a, for x64 (/usr/lib/gcc/x86_64-linux-gnu/13/) and x86
    (the multilib copy in .../13/32/, from lib32gcc-13-dev, the same package
    version). These are the archives every gcc13 build of this corpus links.
  * mingw-w64 GCC 13.2.0 (13.2.0-6ubuntu1+26.1, win32 thread model) libgcc.a
    and libgcc_eh.a, x64 and x86, from gcc-mingw-w64-x86-64-win32 and
    gcc-mingw-w64-i686-win32: the archives every mingw13 build links.

The compiler is not run to produce any of the code. SMDA has no COFF or ar
loader, so the same method as libgcc_harvest.py is used: the archive is linked
whole (--whole-archive) into one shared object, for disassembly and never for
execution. The ELF image is linked -no-pie -nostartfiles with entry address
zero against the dynamic host libc, so libc bodies do not enter the family;
the PE image is a DLL linked -nostartfiles -nodefaultlibs with entry address
zero, plus the msvcrt and kernel32 import libraries. The runtime filter
(drop_crt_glue) is off because the runtime is the subject.

What the PE link needed beyond the two archives, each recorded with the exact
linker error that showed it. The first PE build left the default libraries on,
and the linker pulled the members libgcc_eh needs out of libmingwex into the
image under libgcc's name: 77 (x64) and 82 (x86) named functions that neither
archive defines (__mingw_pformat, __gdtoa, __Balloc_D2A, __mingwthr_*,
wcrtomb, ...), found by comparing every named function of the image with the
nm of the two archives (the ELF images had 0). -nodefaultlibs then failed with
"harvested/libgcc_eh.a(emutls.o):(.text+0x292): undefined reference to
`__imp_InitializeCriticalSection'" (collect2: error: ld returned 1 exit
status; --unresolved-symbols=ignore-all does not stop this PE linker from
failing, and --noinhibit-exec still exits non-zero), so the import libraries
-lmsvcrt -lkernel32 resolve the Windows API and C runtime calls as import
thunks of one instruction each. Three symbols remain, __CRT_MT (_CRT_MT on
x64), __mingw_vfprintf and __mingwthr_key_dtor, which live in the CRT objects
the build does not link; they are defined by a generated stub (below). Last,
the GNU linker adds a runtime-pseudo-relocation table to a DLL that holds
libgcc_eh's references, and that table points at _pei386_runtime_relocator,
which lives in the startup object that -nostartfiles leaves out
("m_x86_64_dll_ertr000001.o:(.rdata+0x0): undefined reference to
`_pei386_runtime_relocator'"; --disable-runtime-pseudo-reloc crashes this ld
with "*** buffer overflow detected ***: terminated" and --defsym fails with
"relocation truncated to fit: IMAGE_REL_AMD64_ADDR32NB"). The recipe generates
stub.c with empty definitions of those four names (a build step; nothing of
upstream is patched). They, and the import thunks, are named functions of one
to a few instructions (below the 10-instruction comparison floor) that stay in
the image because this branch has no by-name exclusion; the archives' own
members are all linked unchanged.

The pinned archives are verified by sha256 in the first build step, so a host
with a different toolchain build fails loudly instead of recording another
GCC under these names. The staging source is the zlib tarball, as in
libgcc_harvest.py; none of it is built or linked.

Measured on the artefacts (SMDA 5.0.2; kept + removed = image total, removed
is 0 everywhere because the runtime filter is off; functions of 10 or more
instructions / their distinct PicHashes):

  libgcc_13.3.0-ubuntu24.04_gcc13_x64_libgcc.elf   675 + 0 = 675   491 / 459
  libgcc_13.3.0-ubuntu24.04_gcc13_x86_libgcc.elf   651 + 0 = 651   542 / 541
  libgcc_13.2.0-mingw-w64_mingw13_x64_libgcc.dll   583 + 0 = 583   424 / 399
  libgcc_13.2.0-mingw-w64_mingw13_x86_libgcc.dll   567 + 0 = 567   468 / 438

PicHash overlap between any two of these four, and between each and the GCC
4.1.2 and 4.2.1 images of libgcc_harvest.py (same architecture): 0 shared in
every pairing (4.1.2 against 4.2.1 share 11 on x64 and 4 on x86). Linux x64
against x86 and MinGW against Linux are different code (calling convention,
PIC), so nothing is shared there either.

Every named function of the two ELF images is a symbol that libgcc.a or
libgcc_eh.a defines (checked against nm of the archives: 0 outside). The PE
images have 13 named functions outside the archives, all of the link and not
of libgcc, each 1 instruction except __acrt_iob_func (14 instructions on x64,
7 on x86; PicHash 4602613404736419017 and 6992788135605358105) and
__mingw_vfprintf (2): _pei386_runtime_relocator, __mingw_vfprintf,
__mingwthr_key_dtor, the import thunks abort, calloc, fflush, free, malloc,
memcpy, memset, realloc (x86 also strlen) and __iob_func (x64). The
x64 PE image has 23 and the x86 PE image 44 unnamed functions of 10 or more
instructions; they are members of the two archives that carry no symbol of
their own and were not located one by one. The first PE build (default
libraries on) had 649 and 636 functions with 77 and 82 of libmingwex's.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_STAGE = Source(
    url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
    sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23")

# sha256 of (libgcc.a, libgcc_eh.a) per toolchain.
_LINUX = {
    "x64": ("d9376c55f97863a4e5fbb6c6beca2591b319bf786f3a7ca56da8964c5662171f",
            "f853cbbf842ff8714cc8dd986e2fd5bb309d34d490b0707203223ee4d52c76bc"),
    "x86": ("b99668672d6303fdd975665e4f7e85a9309f8cae3c7bb268e2e11525bd223ce5",
            "b14a6a6edbc84c2bfcc8e40fde8e3a7553c37f7f6db612ddcb482152f5855c90"),
}
_MINGW = {
    "x64": ("c1a90d312951343e55713afee958164017c91240ec197a32e4f74acb83708385",
            "6fe10b8ec2d01e2d0aeb413729bbc588044c5e76d648f8ee739a0fbaaf452abd"),
    "x86": ("af096e7591413be61256c91cfb6f7e69053e80b80f7aa33015ec9c39323c96ed",
            "5293c2d05371a56b0d66893d47474ca5f75550754f3d90d9259b462e753732b2"),
}


def _locate(sums):
    """Resolve both archives through the compiler, then verify their digests."""
    return [
        BuildStep("mkdir -p harvested"),
        BuildStep(
            "LIBGCC=$({cc} {archflag} -print-file-name=libgcc.a) && "
            "LIBGCC_EH=$({cc} {archflag} -print-file-name=libgcc_eh.a) && "
            "echo \"%s  $LIBGCC\" | sha256sum -c - && "
            "echo \"%s  $LIBGCC_EH\" | sha256sum -c - && "
            "cp \"$LIBGCC\" harvested/libgcc.a && "
            "cp \"$LIBGCC_EH\" harvested/libgcc_eh.a" % sums),
    ]


RECIPES = {}

for _arch in ("x86", "x64"):
    RECIPES["libgcc_13.3.0_ubuntu24.04_" + _arch] = Recipe(
        family="libgcc", version="13.3.0-ubuntu24.04",
        upstream="https://gcc.gnu.org/; https://packages.ubuntu.com/noble/libgcc-13-dev",
        license="GPL-3.0-or-later with GCC runtime library exception 3.1 (GCC 13.3.0)",
        source=_STAGE,
        build=_locate(_LINUX[_arch]) + [
            BuildStep("{cc} {archflag} -no-pie -nostartfiles -Wl,-e,0 "
                      "-Wl,--whole-archive harvested/libgcc.a harvested/libgcc_eh.a "
                      "-Wl,--no-whole-archive -lc -o libgcc.elf"),
        ],
        artifacts=[Artifact(path="libgcc.elf", component="libgcc.elf")],
        toolchains=["linux_" + _arch], requires=["tar"], drop_crt_glue=False,
        build_flags="Prebuilt GCC 13.3.0 libgcc.a + libgcc_eh.a of the host toolchain "
                    "(Ubuntu 13.3.0-6ubuntu2~24.04.1); host link only: -no-pie "
                    "-nostartfiles -Wl,-e,0 -Wl,--whole-archive; dynamic libc",
        notes="Harvested from the prebuilt gcc13 toolchain (Ubuntu 24.04, "
              "libgcc-13-dev / lib32gcc-13-dev 13.3.0-6ubuntu2~24.04.1), not "
              "rebuilt; archives pinned by sha256 in the build. The host linker "
              "links both archives whole into an ELF with entry address zero, "
              "no startup, dynamic host libc; the image is not runnable. "
              "The runtime filter is off because libgcc is the subject. "
              "zlib supplies only the staging directory; none of it is linked.",
    )

for _arch in ("x86", "x64"):
    RECIPES["libgcc_13.2.0_mingw_w64_" + _arch] = Recipe(
        family="libgcc", version="13.2.0-mingw-w64",
        upstream="https://gcc.gnu.org/; https://www.mingw-w64.org/",
        license="GPL-3.0-or-later with GCC runtime library exception 3.1 (GCC 13.2.0)",
        source=_STAGE,
        build=_locate(_MINGW[_arch]) + [
            # The linker's runtime-pseudo-relocation table needs this symbol
            # from the startup object that -nostartfiles omits; see the
            # module docstring.
            BuildStep("printf 'void _pei386_runtime_relocator(void) {}\\n"
                      "int _CRT_MT;\\nint __mingw_vfprintf(void) { return 0; }\\n"
                      "void __mingwthr_key_dtor(void) {}\\n' > stub.c"),
            BuildStep("{cc} -O2 -c stub.c -o stub.o"),
            BuildStep("{cc} -shared -nostartfiles -nodefaultlibs -Wl,-e,0 stub.o "
                      "-Wl,--whole-archive harvested/libgcc.a harvested/libgcc_eh.a "
                      "-Wl,--no-whole-archive -lmsvcrt -lkernel32 -o libgcc.dll"),
        ],
        artifacts=[Artifact(path="libgcc.dll", component="libgcc.dll")],
        toolchains=["mingw_" + _arch], requires=["tar"], drop_crt_glue=False,
        build_flags="Prebuilt mingw-w64 GCC 13.2.0 (win32 threads) libgcc.a + "
                    "libgcc_eh.a (Ubuntu 13.2.0-6ubuntu1+26.1); host link only: "
                    "-shared -nostartfiles -nodefaultlibs -Wl,-e,0 -Wl,--whole-archive "
                    "plus the msvcrt and kernel32 import libraries",
        notes="Harvested from the prebuilt mingw-w64 GCC 13.2.0 toolchain "
              "(gcc-mingw-w64-{x86-64,i686}-win32 13.2.0-6ubuntu1+26.1), not "
              "rebuilt; archives pinned by sha256 in the build. SMDA has no "
              "COFF/ar loader, so both archives are linked whole into a DLL with "
              "entry address zero and no startup; the image is not runnable. "
              "Four generated empty definitions (_pei386_runtime_relocator, "
              "_CRT_MT, __mingw_vfprintf, __mingwthr_key_dtor) and the msvcrt/"
              "kernel32 import thunks the link needs stay in the image as "
              "named functions of one to a few instructions. The runtime "
              "filter is off because "
              "libgcc is the subject. zlib supplies only the staging directory.",
    )

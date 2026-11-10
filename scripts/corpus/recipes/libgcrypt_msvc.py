"""libgcrypt built with cl, beside the MinGW and ELF builds of the same release.

THESE IMAGES ARE NOT BYTE-IDENTICAL TO A BUILD OF UNMODIFIED UPSTREAM. Two
things differ from the MinGW and ELF legs, and both change the code:

  1. --disable-asm. cl cannot assemble libgcrypt's GNU-syntax .S modules (81 of
     them) or the GCC inline assembler its C files use, so configure is run with
     --disable-asm and the generic C paths are compiled: mpi/generic/*.c for the
     multi-precision primitives, plain C for AES, the hashes, ChaCha20 and the
     rest, and no hardware-accelerated code (src/hwf-x86.c is compiled, but
     without CPUID code, so it reports no hardware features, and no AES-NI,
     PCLMUL, AVX2, SHA-NI or RDRAND code exists in these images). The MinGW and
     ELF legs were built with upstream's defaults, assembler modules and hardware
     acceleration on. A function present in one family of legs may therefore not
     exist in the other (the amd64 assembler entry points) and the C ones that
     exist in both are compiled by a different compiler.
     In 1.8.14 --disable-asm does not remove the amd64 modules from the cipher
     object list (configure adds them for any x86_64 host); they are not
     assembled, and nothing in the C code references them because the
     HAVE_COMPATIBLE_GCC_AMD64_PLATFORM_AS / WIN64 macros that gate the calls
     are not defined.
  2. Build-tree source edits in four files (six hunks), listed below. cl has no variable-length
     arrays; the five source locations that use them are rewritten in the build
     tree by the driver (exercisers/gnupg_cl.py, PATCHES, applied as the first
     step after configure) and each applied edit is printed as a unified diff
     into the build log. Nothing is committed into a source tree. Where the bound
     is already a constant expression the array size is spelled as that
     expression; where it is a run-time value the array becomes a pointer to
     _alloca() storage of the same element count, which is what a VLA is.
     sizeof is never applied to any of these arrays (checked).

Upstream is autotools only and `make` cannot run on the windows-2022 runner
(configure is started as /d/a/.../configure, the runner's native-Windows GNU
Make 4.4.1 cannot see that path, and remakes Makefile.in/configure/config.status
forever: `File '.../Makefile.in' does not exist.`). So configure runs for real,
with `CC="build-aux/compile cl -nologo"` and a *-mingw32* host triple (what
selects the Windows code), `--disable-static --enable-shared --disable-doc
--disable-asm --with-libgpg-error-prefix=...` and `ac_cv_type_pid_t=yes` (the
autoconf default would #define pid_t __int64 on Win64, against gcrypt.h's own
`typedef int pid_t`); the object list of each of compat, mpi, cipher, random and
src is read from the generated Makefiles; cipher/gost-sb.h is generated with
upstream's cipher/gost-s-box.c built by the runner's MinGW gcc (a build-host
helper, not in the artefact); every translation unit is compiled with
`cl /MD /O2 /Z7` (no /GL; rndjent.c with /Od as upstream builds it unoptimised),
and the DLL is linked from the shipped src/libgcrypt.def with /DLL /DEBUG
/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF against the paired libgpg-error
built by libgpg_error_msvc.py in the same step.

Build-side shims (written by the driver, not part of upstream): <unistd.h>
(ssize_t as long, pid_t as int, F_OK/R_OK/W_OK/X_OK, S_IRUSR/S_IWUSR/S_IXUSR),
an empty <sys/file.h> and <sys/time.h>, command-line defines
__thread=__declspec(thread) with HAVE_GCC_STORAGE_CLASS__THREAD=1 (1.11.3's
fips.c refuses to compile without thread-local storage), and
strcasecmp=_stricmp, strncasecmp=_strnicmp.

Further build-side measures, none of which edits a source file:
  * configure cache values `ac_cv_type_pid_t=yes` and `ac_cv_func_memmove`,
    `strtoul`, `atexit`, `raise`, `strerror`, `rand`, `stricmp` = yes: its link
    tests misreport these CRT functions under cl, and g10lib.h would then
    rename memmove to bcopy (an unresolved external);
  * mpi/config.links did not select the standard multi-precision primitives in
    this configure run (mpih-add1, -sub1, -mul1, -mul2, -mul3, -lshift,
    -rshift are missing from the generated mpi/Makefile, so the DLL lacked
    _gcry_mpih_add_n and its relatives); the driver adds mpi/generic/<name>.c
    for each, which is the file config.links chooses when assembler modules are
    off;
  * src/hwf-x86.c (1.8.14 lists it for every x86 host) is compiled with
    /D__x86_64__ (/D__i386__ on x86); without a GCC CPU macro it #errors, and
    with only that macro (no __GNUC__) it compiles its CPUID-less fallback,
    which reports no hardware features;
  * the amd64 `.S` modules that 1.8.14's configure adds for every x86_64 host
    even with --disable-asm are not assembled (24 on x64; 2 ARM ones are
    listed on both), and nothing in the C code calls them.

hwfeatures.c in 1.10.4 and 1.11.3. cl 19.44.35229 aborted on src/hwfeatures.c
with `fatal error C1001: Internal compiler error.` at every optimiser setting.
The driver compiles ten variants of that one file in the build log; the result
(run 42408972437, x86 and x64, both versions) is that the crash is the table
`hwflist[] = { ... }`: with --disable-asm HAVE_CPU_ARCH_X86 is not defined, the
`#if defined(HAVE_CPU_ARCH_X86) ... #elif ... #endif` chain leaves the
initialiser empty, and cl cannot compile an empty brace list for an array of
structs. Removing the hwf.deny parser, or the _gcry_get_sysconfdir code, or
both, still crashes; /std:c11, /Zc:preprocessor, /Od /Zi and /d2SSAOptimizer-
still crash; `/DHAVE_CPU_ARCH_X86=1` for that one file compiles. That is a
command-line define and edits no source. Its consequences, stated exactly: the
table gets its x86 rows (padlock, AES-NI, ... names) so `--disable-hw-feature`
style names are accepted, and _gcry_detect_hw_features calls
_gcry_hwf_detect_x86, which src/hwf-x86.c provides; that file is compiled
(with /D__x86_64__ or /D__i386__, as for 1.8.14) without CPUID code and
reports no features. 1.8.14 is not affected (its table has unconditional rows).
So the 1.10.4 and 1.11.3 images contain src/hwf-x86.c and a populated feature
name table that the generic --disable-asm build would not otherwise have.

Measured on the artefacts (kept + removed = every function in the image; the
removed count is the compiler and CRT glue the baseline recognised):

    1.8.14  x86 PE 1787 + 160 = 1947    x64 PE 1788 + 165 = 1953
    1.10.4  x86 PE 2243 + 162 = 2405    x64 PE 2253 + 167 = 2420
    1.11.3  x86 PE 2722 + 162 = 2884    x64 PE 2724 + 163 = 2887

PicHash overlap of the functions with 10 or more instructions between these
images and the MinGW and ELF images of the same version and architecture:
1.8.14 x64 0 of 934 (MinGW) and 0 of 975 (ELF), x86 2 of 857 (MinGW, 0.2%) and
0 of 1059 (ELF); 1.10.4 x64 3 of 1164 (0.3%) and 0 of 1208, x86 2 of 1063 and
0 of 1282; 1.11.3 x64 3 of 1408 and 0 of 1447, x86 2 of 1240 and 0 of 1464;
libgpg-error 1.35 and 1.61 share 0 with their MinGW and ELF builds
on both architectures. The code surface differs in the two ways stated at the
top (generic C instead of assembler and hardware-accelerated paths, compiled by
cl instead of gcc, plus the edits below), so the images are separate reference
data rather than duplicates.

The edits as applied (unified diffs, context 1):

  ## libgcrypt-1.8.14
    --- a/cipher/cipher-ccm.c
    +++ b/cipher/cipher-ccm.c
    @@ -42,3 +42,3 @@
       gcry_cipher_encrypt_t enc_fn = c->spec->encrypt;
    -  unsigned char tmp[blocksize];
    +  unsigned char tmp[16]; /* blocksize */
       unsigned int burn = 0;
  ## libgcrypt-1.10.4
    --- a/cipher/cipher-ccm.c
    +++ b/cipher/cipher-ccm.c
    @@ -42,3 +42,3 @@
       gcry_cipher_encrypt_t enc_fn = c->spec->encrypt;
    -  unsigned char tmp[blocksize];
    +  unsigned char tmp[16]; /* blocksize */
       unsigned int burn = 0;
    --- a/mpi/ec.c
    +++ b/mpi/ec.c
    @@ -587,4 +587,4 @@
       mpi_size_t wsize = (256 + BITS_PER_MPI_LIMB - 1) / BITS_PER_MPI_LIMB;
    -  mpi_limb_t n[wsize + 1];
    -  mpi_limb_t s[wsize + 1];
    +  mpi_limb_t n[(256 + BITS_PER_MPI_LIMB - 1) / BITS_PER_MPI_LIMB + 1];
    +  mpi_limb_t s[(256 + BITS_PER_MPI_LIMB - 1) / BITS_PER_MPI_LIMB + 1];
       mpi_limb_t cy, borrow;
  ## libgcrypt-1.11.3
    --- a/cipher/mceliece6688128f.c
    +++ b/cipher/mceliece6688128f.c
    @@ -1902,4 +1902,5 @@
     {
    -  int32 temp[2*n];
    -  int16 pi_test[n], diff;
    +  int32 *temp = (int32 *) _alloca (sizeof (int32) * (2*n));
    +  int16 *pi_test = (int16 *) _alloca (sizeof (int16) * n);
    +  int16 diff;
       int i;
    --- a/cipher/sntrup761.c
    +++ b/cipher/sntrup761.c
    @@ -270,6 +270,6 @@
         {
    -      uint16_t R2[(len + 1) / 2];
    -      uint16_t M2[(len + 1) / 2];
    -      uint16_t bottomr[len / 2];
    -      uint32_t bottomt[len / 2];
    +      uint16_t *R2 = (uint16_t *) _alloca (sizeof (uint16_t) * ((len + 1) / 2));
    +      uint16_t *M2 = (uint16_t *) _alloca (sizeof (uint16_t) * ((len + 1) / 2));
    +      uint16_t *bottomr = (uint16_t *) _alloca (sizeof (uint16_t) * (len / 2));
    +      uint32_t *bottomt = (uint32_t *) _alloca (sizeof (uint32_t) * (len / 2));
           long long i;
    --- a/cipher/sntrup761.c
    +++ b/cipher/sntrup761.c
    @@ -343,4 +343,4 @@
         {
    -      uint16_t R2[(len + 1) / 2];
    -      uint16_t M2[(len + 1) / 2];
    +      uint16_t *R2 = (uint16_t *) _alloca (sizeof (uint16_t) * ((len + 1) / 2));
    +      uint16_t *M2 = (uint16_t *) _alloca (sizeof (uint16_t) * ((len + 1) / 2));
           long long i;
    --- a/cipher/sntrup761.c
    +++ b/cipher/sntrup761.c
    @@ -697,3 +697,3 @@
     {
    -  unsigned char x[inlen + 1];
    +  unsigned char *x = (unsigned char *) _alloca (inlen + 1);
       unsigned char h[64];
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .libgcrypt import PAIRING, _BASE, _GPGERR_SHA256, _GPGERR_URL, _SHA256

_PY = ("python {repo}/scripts/corpus/exercisers/gnupg_cl.py {arch} gcrypt "
       "{source_root} {gpg_error}")


def _gc(version):
    err = PAIRING[version]
    return Recipe(
        family="libgcrypt", version=version,
        upstream="https://gnupg.org/software/libgcrypt/",
        license="LGPL-2.1-or-later (library), GPL-2.0-or-later (tests and tools)",
        source=Source(url=_BASE % version, sha256=_SHA256[version]),
        extra_sources={"gpg_error": Source(url=_GPGERR_URL % err,
                                           sha256=_GPGERR_SHA256[err])},
        build=[BuildStep(_PY)],
        artifacts=[Artifact(path="msvc-{arch}/gc/src/libgcrypt-20.dll",
                            component="libgcrypt-20.dll",
                            pdb="msvc-{arch}/gc/src/libgcrypt-20.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Z7 (no /GL), --disable-asm (generic C, no hardware "
                    "acceleration); /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
                    "/OPT:NOICF at link; configure by upstream, no make; "
                    "BUILD-TREE SOURCE EDITS (variable-length arrays) - not "
                    "byte-identical to unmodified upstream",
        notes="Shared libgcrypt built with cl from the signed GnuPG release "
              "tarball, linked against the paired libgpg-error %s built in the "
              "same step. NOT a build of unmodified upstream: configured with "
              "--disable-asm (generic C code, none of the amd64/AVX/AES-NI "
              "modules the MinGW and ELF legs contain) and with build-tree "
              "edits that replace variable-length arrays, which cl does not "
              "support, by constant-size arrays or _alloca() storage "
              "(cipher/cipher-ccm.c, mpi/ec.c, cipher/mceliece6688128f.c, "
              "cipher/sntrup761.c, as present in the release). The edits are "
              "applied by the build driver and printed as diffs in the build "
              "log; they are reproduced in the module docstring of "
              "scripts/corpus/recipes/libgcrypt_msvc.py. Upstream's make cannot "
              "run on the runner, so configure runs for real and the compile "
              "and link steps are reproduced from its generated Makefiles." % err,
    )


_BUILT = ("1.8.14", "1.10.4", "1.11.3", "1.10.3", "1.8.5")
RECIPES = {"libgcrypt_%s_msvc" % v: _gc(v) for v in _BUILT}


# The assembly variant: the issue (r0ny123/mcrit-data#25) asks for the
# assembler modules, and cl cannot reach them (gnupg_cl.py, ASM, says why), so
# the C and the .S files of libgcrypt are compiled with clang-cl for the MSVC
# ABI and runtime and linked by link.exe like the other MSVC images; nothing
# is edited (clang has variable-length arrays). Own version slug, so the cl
# images keep theirs.
def _gc_asm(version):
    recipe = _gc(version)
    recipe.version = version + "-clangcl"
    recipe.build = [BuildStep(_PY, env={"GNUPG_CL_ASM": "1"})]
    recipe.build_flags = (
        "C and assembly compiled by clang-cl (LLVM, MSVC ABI) with "
        "/clang:-fgnuc-version=4.2.1, /MD /O2 /Z7 (no /GL), assembler modules "
        "on (no --disable-asm); /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
        "/OPT:NOICF at link (link.exe); configure by upstream, no make; no "
        "source edits; libgpg-error built with cl")
    recipe.notes = (
        "Shared libgcrypt from the signed GnuPG release tarball with its "
        "assembler modules and hardware acceleration, for the MSVC ABI and the "
        "DLL runtime. cl cannot build this configuration: the C code that "
        "dispatches to the assembly is gated on GCC's predefined macros and the "
        "inline-assembly files are GCC syntax, so every libgcrypt translation "
        "unit, C and assembly, is compiled by clang-cl "
        "presenting itself as GCC 4.2.1; the provenance compiler field names "
        "the toolchain's cl, which built the paired libgpg-error %s. No "
        "upstream file is edited. See scripts/corpus/exercisers/gnupg_cl.py."
        % PAIRING[version])
    return recipe


RECIPES.update({"libgcrypt_%s_asm_msvc" % v: _gc_asm(v) for v in _BUILT})

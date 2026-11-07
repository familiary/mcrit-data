"""libgcrypt built with cl, beside the MinGW and ELF builds of the same release.

THESE IMAGES ARE NOT BYTE-IDENTICAL TO A BUILD OF UNMODIFIED UPSTREAM. Two
things differ from the MinGW and ELF legs, and both change the code:

  1. --disable-asm. cl cannot assemble libgcrypt's GNU-syntax .S modules (81 of
     them) or the GCC inline assembler its C files use, so configure is run with
     --disable-asm and the generic C paths are compiled: mpi/generic/*.c for the
     multi-precision primitives, plain C for AES, the hashes, ChaCha20 and the
     rest, and no hardware detection (hwf-x86.c is not built, so no AES-NI,
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


RECIPES = {"libgcrypt_%s_msvc" % v: _gc(v) for v in _SHA256}

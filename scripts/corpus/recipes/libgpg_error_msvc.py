"""libgpg-error built with cl, beside the MinGW and ELF builds of the same release.

Only 1.35 is registered. 1.61 gets as far as the link and stops on one
unresolved external (see "Not built" below), and libgcrypt does not build at
all; both are recorded in "Targets investigated but not built" in
scripts/corpus/README.md.

Why not `make`. Upstream is autotools only. Under MSYS2 on the windows-2022
runner `make` never compiles an object: configure is run as
/d/a/.../configure, the runner's GNU Make 4.4.1 is a native-Windows build that
cannot see that path (`File '.../Makefile.in' does not exist.`), and so it
remakes Makefile.in, configure and config.status forever (autoconf and automake
are stubbed with `:`). So `make` is not used at all.

What is run instead (exercisers/gnupg_cl.py, no upstream source is edited):

  * upstream's own configure, `CC="build-aux/compile cl -nologo"`, with a
    `*-mingw32*` host triple (configure.ac selects the Windows code only for
    that), `--disable-static --enable-shared --disable-doc --disable-tests
    --disable-languages --disable-nls`;
  * the object list is read from the generated src/Makefile
    (am_libgpg_error_la_OBJECTS plus libgpg_error_la_LIBADD), so it is
    upstream's list; the resource object (versioninfo.lo) is not compiled;
  * the generated files make would produce are produced with upstream's own awk
    scripts and helper sources: code-to-errno.h (mkerrnos.awk),
    mkerrcodes.h (mkerrcodes1.awk, cl /EP, mkerrcodes.awk), mkerrcodes.c
    compiled with cl and run for code-from-errno.h (mkerrcodes2.awk),
    gpg-error.h and gpgrt.h from mkheader, and gpg-error.def from
    gpg-error.def.in through the preprocessor. mkheader.c includes
    <unistd.h> and does not compile with cl, so the runner's MinGW gcc builds
    that build-host helper; it is not part of the artefact;
  * every translation unit is compiled with `cl /MD /O2 /Z7`, no /GL;
  * the DLL is linked with /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF
    /OPT:NOICF and the .def file generated above.

Build-side shims, written by the driver and not part of upstream: a directory
placed on the include path with <unistd.h> (declares ssize_t as `long` and pid_t
as `int`, the same types gcrypt.h declares for non-GNU compilers, plus
F_OK/R_OK/W_OK/X_OK and S_IRUSR/S_IWUSR/S_IXUSR), an empty <sys/file.h>, and
one wrapper translation unit, visibility_cl.c, which includes upstream's
unchanged visibility.c after defining GPGRT_HAVE_MACRO_FUNCTION. That define is
needed because gpg-error.h only sets it for GCC while visibility.c calls the
four-argument _gpgrt__log_assert with three arguments without it
(`error C2198: ... too few arguments for call`); __FUNCTION__ is a cl builtin.
No file under the source tree is modified.

The code surface is the Windows one (w32-*.c, spawn-w32.c) that the MinGW build
also compiles, but compiled by cl: no GCC attributes, `long` is 32 bits for
ssize_t on x64 where MinGW's is 64, and x86 uses cl's calling-convention and
CRT-import conventions. The DLL imports the UCRT/VCRT (/MD) where the MinGW DLL
imports msvcrt.

Not built: 1.61. Same driver, 26 of 26 translation units compile, and the link
stops with `libgpg_error_la-argparse.obj : error LNK2019: unresolved
external symbol strcasecmp referenced in function handle_meta_user`; cl has
strcasecmp only as _stricmp. A command-line define would address it; it has not
been run.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .libgpg_error import _BASE, _SHA256

_PY = "python {repo}/scripts/corpus/exercisers/gnupg_cl.py {arch} gpg-error {source_root}"


def _ge(version):
    return Recipe(
        family="libgpg-error", version=version,
        upstream="https://gnupg.org/software/libgpg-error/",
        license="LGPL-2.1-or-later (library), GPL-1.0-or-later (tools)",
        source=Source(url=_BASE % version, sha256=_SHA256[version]),
        build=[BuildStep(_PY)],
        artifacts=[Artifact(path="msvc-{arch}/ge/src/libgpg-error-0.dll",
                            component="libgpg-error-0.dll",
                            pdb="msvc-{arch}/ge/src/libgpg-error-0.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Z7 (no /GL); /DEBUG /Brepro /INCREMENTAL:NO "
                    "/OPT:NOREF /OPT:NOICF at link; configure by upstream, no make",
        notes="Shared libgpg-error built with cl from the signed GnuPG release "
              "tarball. Upstream's `make` cannot run on the runner, so configure "
              "runs for real and the generated headers and the compile and link "
              "steps are reproduced by exercisers/gnupg_cl.py from upstream's own "
              "generated Makefiles, awk scripts and helper sources. Build-side "
              "shim headers (unistd.h, sys/file.h) and one wrapper translation "
              "unit for visibility.c are written by the driver; no upstream file "
              "is modified. See the module docstring.",
    )


RECIPES = {"libgpg-error_%s_msvc" % v: _ge(v) for v in ("1.35",)}

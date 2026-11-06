"""libgpg-error - the GnuPG project's error codes and "gpgrt" runtime.

libgcrypt, GnuPG, libassuan, gpgme, pinentry and the rest of the GnuPG suite
link it, so it turns up inside anything that carries libgcrypt. Nothing in the
corpus covered it under any name. It is its own family rather than a component
of libgcrypt: libgcrypt imports it (libgpg-error-0.dll, libgpg-error.so.0)
instead of containing it, so the two families describe disjoint code, and a
sample that statically links only one of them should match only that one.

Two versions, both signed releases from https://gnupg.org/ftp/gcrypt/libgpg-error/.
Upstream publishes a detached .sig per tarball and no checksum file; each
tarball below verified with gpg against the GnuPG release keys (EdDSA
6DAA6E64A76D2840571B4902528897B826403ADA "Werner Koch (dist signing 2020)" for
1.61, and the RSA dist keys D8692123C4065DEA5E0F3AB5249B39D24F25E3B6 and
031EC2536E580D8EA286A9F22071B08A33BD3F06 for 1.35, fetched from
keyserver.ubuntu.com - both are expired, the signatures are good), and the
sha256 pinned here is of the verified file. 1.61 (2026-05-07) is the newest
release; 1.35 (2018) is what the 1.8.x libgcrypt line was shipped with
(Debian 10, RHEL 8 and Ubuntu 20.04 carry 1.31-1.37).

Why these two and not three. 1.47 (Debian 12 / Ubuntu 24.04) was built and
measured, then dropped. PicHash overlap of the functions with 10 or more
instructions between releases, per artefact:

    x64 MinGW   1.35 vs 1.47 54%    1.47 vs 1.61 80%    1.35 vs 1.61 47%
    x64 ELF     1.35 vs 1.47 82%    1.47 vs 1.61 77%    1.35 vs 1.61 73%
    x86 MinGW   1.35 vs 1.47 55%    1.47 vs 1.61 80%    1.35 vs 1.61 48%
    x86 ELF     1.35 vs 1.47  6%    1.47 vs 1.61  7%    1.35 vs 1.61  6%

1.47 is a 77-80% near duplicate of 1.61 on every PE and x64 leg, the same
threshold at which libpcap dropped 1.10.1, so it adds files and no reference
value. 1.35 and 1.61 share 47-73% on those legs, and the x86 ELF figures are
the per-image GOT delta described in the README's "The Linux half".

Which libgcrypt links which libgpg-error. The libgcrypt recipes build their
own copy of the paired release from the same pinned tarball with the same
configure options (configure_options below is shared), so the libgpg-error a
libgcrypt artefact was linked against is byte-identical to the one in this
family, on the same axis (MinGW x86/x64, ELF x86/x64):

    libgcrypt 1.11.3  (needs >= 1.49)  ->  libgpg-error 1.61
    libgcrypt 1.10.4  (needs >= 1.27)  ->  libgpg-error 1.61
    libgcrypt 1.8.14  (needs >= 1.25)  ->  libgpg-error 1.35

The minimums are NEED_GPG_ERROR_VERSION in each libgcrypt's configure.ac. 1.11
cannot use 1.35. 1.10 and 1.8 accept either, and the pairing follows era: 1.35
for the old line, the newest for the other two. What the pairing changes in a
libgcrypt artefact is only its import table and the gpg-error.h macros it was
compiled against.

Shared, not static. SMDA has no COFF/ar loader, so a static archive could not
be read at all, and the shared object is also the form the Windows GnuPG
distributions and every Linux package ship (libgpg-error-0.dll,
libgpg-error.so.0). The MinGW DLL imports msvcrt and KERNEL32; the ELF object
NEEDs glibc, so no C library body is linked in.

Axes. MinGW x86/x64 and Linux ELF x86/x64 (gcc 13.3, glibc), both built here.
They are distinct: PicHash overlap of the 10+ instruction functions between the
MinGW and the ELF artefact of the same version is 0 on x64 for both versions
(the host gcc defaults to -fcf-protection=full, so x64 ELF functions begin
with endbr64 - 654 of them in the 1.61 object - which the MinGW compiler does
not emit) and 1 (1.35) and 14 (1.61) on x86, about 0.4% and 4%. MSVC is not
built: see "Targets investigated but not built" in scripts/corpus/README.md.

Build. Upstream's own configure and make, out of tree, one directory per
architecture, no source patch. Options: --disable-static --enable-shared
--disable-doc --disable-tests --disable-languages --disable-nls (NLS is off so
the result does not depend on whether the host has gettext, which this one
does not; options a release predates are reported by configure as unrecognised
and ignored). MinGW is --host=<triple>; the ELF build is native and the
32-bit leg takes -m32 from the toolchain's CC. Three things about the builds:

  * The x64 MinGW DLL of 1.35 is named libgpg-error6-0.dll by upstream and the
    x86 one libgpg-error-0.dll; a copy step gives both the x86 name so that
    the two architectures carry one component. (1.61 names both
    libgpg-error-0.dll; the copy is then a no-op.)
  * 1.35 predates GCC 10's -fno-common default and defines
    _gpgrt_functions_w32_pollable as a tentative definition in several
    translation units, so the MinGW x64 link stops with "multiple definition".
    CFLAGS gets -fcommon for every 1.35 build, ELF included.
  * `make install` is not run for the family's own artefacts; the libgcrypt
    recipes run `make -C src install` only, because the top-level install hook
    calls msgfmt.

Licence, as recorded upstream: the library is LGPL-2.1-or-later; the gpg-error
command and the tests are GPL-1.0-or-later (the source tree's COPYING and
COPYING.LIB). No source from the tree is stored here.

Measured on the artefacts (kept + removed = every function in the image; the
removed count is the compiler runtime the baseline recognised):

    1.35  x86 ELF 595 + 5 = 600      x64 ELF 577 + 5 = 582
          x86 PE  430 + 138 = 568    x64 PE  500 + 135 = 635
    1.61  x86 ELF 712 + 5 = 717      x64 ELF 706 + 5 = 711
          x86 PE  579 + 138 = 717    x64 PE  666 + 136 = 802

Glue the baseline left in, by name and PicHash (hex, instructions in
brackets). None on the PE legs: DllMain and module_init are libgpg-error's own.
The ELF legs carry the usual crtstuff residue, which the README describes: on
x64 only atexit a8772f94e5724ae8 (4), in both versions; on x86, for 1.35 and
1.61 respectively, _init 62ef7ee7150fb913 / 2cfe743671a68604 (11),
register_tm_clones b3bcb581243f8e90 / 37a376a86012a1f6 (26),
deregister_tm_clones ef7a4e856e31e360 / 0c289fdb5ac73e56 (18),
__do_global_dtors_aux e39aa938b5bb0700 / 839bf3c85447c5d6 (21),
__stack_chk_fail_local 7135451cb1bcdf34 / 9f76bdebef114213 (5),
atexit 297160e782b68c56 / 75b738ddddaa2b69 (11), and __x86.get_pc_thunk.bp
7c99608cc56520ba, .cx 769f0aed4b5feefe and .si 99104660fd4df449 (2 each, the
same in both versions). Not edited into the baseline.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_BASE = "https://gnupg.org/ftp/gcrypt/libgpg-error/libgpg-error-%s.tar.bz2"

# sha256 of release tarballs whose detached .sig verified with gpg (see the
# docstring); upstream publishes signatures, not checksum files.
_SHA256 = {
    "1.35": "cbd5ee62a8a8c88d48c158fff4fc9ead4132aacd1b4a56eb791f9f997d07e067",
    "1.61": "7a85413f2bc354f4f8aa832b718af122e48965e9e0eb9012ee659c13c6385c93",
}
# libtool file name of the ELF shared object: major 0, then AGE.REVISION.
_SO = {"1.35": "0.26.1", "1.61": "0.42.1"}

# One spelling of the options for this recipe and for the libgcrypt recipes,
# which build the same release as their dependency: the bytes in the two
# places are then the same bytes. NLS is off so the result does not depend on
# whether the host has gettext (this one does not). Switches a release does
# not know (--disable-tests and --disable-languages came after 1.35) are
# reported by configure as unrecognised and ignored.
_OPTIONS = ("--disable-static --enable-shared --disable-doc "
            "--disable-tests --disable-languages --disable-nls")


def configure_options(version):
    """The options for one release, shared with the libgcrypt recipes.

    1.35 predates GCC 10's -fno-common default and defines
    _gpgrt_functions_w32_pollable as a tentative definition in several
    translation units; the MinGW x64 link stops with "multiple definition".
    -fcommon restores the behaviour the release was written for, as a flag
    and not a source change. It is passed to every 1.35 build, ELF included,
    so the four artefacts of that release are compiled the same way.
    """
    if version == "1.35":
        return _OPTIONS + ' CFLAGS="{cflags} -fcommon"'
    return _OPTIONS


def _recipe(version, linux):
    if linux:
        configure = "mkdir -p build-{arch} && cd build-{arch} && " \
                    "{source_root}/configure " + configure_options(version)
        artifact = Artifact(path="build-{arch}/src/.libs/libgpg-error.so.%s"
                            % _SO[version], component="libgpg-error.so")
        toolchains = ["linux_x86", "linux_x64"]
    else:
        configure = "mkdir -p build-{arch} && cd build-{arch} && " \
                    "{source_root}/configure --host={host} " + configure_options(version)
        artifact = Artifact(path="build-{arch}/libgpg-error-0.dll",
                            component="libgpg-error-0.dll")
        toolchains = ["mingw_x86", "mingw_x64"]
    # 1.35 names the x64 DLL libgpg-error6-0.dll and the x86 one
    # libgpg-error-0.dll (1.61 names both -0); the copy gives both one name, so
    # the two architectures carry one component and the README row pairs them.
    extra = [] if linux else [BuildStep(
        "cp src/.libs/libgpg-error*-0.dll libgpg-error-0.dll", cwd="build-{arch}")]
    return Recipe(
        family="libgpg-error",
        version=version,
        upstream="https://gnupg.org/software/libgpg-error/",
        license="LGPL-2.1-or-later (library), GPL-1.0-or-later (tools)",
        source=Source(url=_BASE % version, sha256=_SHA256[version]),
        build=[BuildStep(configure),
               BuildStep("make -j$(nproc)", cwd="build-{arch}")] + extra,
        artifacts=[artifact],
        toolchains=toolchains,
        build_flags="-O2, shared, upstream configure defaults otherwise",
        notes="Shared libgpg-error, "
              + ("the glibc build (native gcc, -m32 for x86)" if linux else
                 "the MinGW-w64 build") + " of the signed GnuPG release "
              "tarball. Imported, not linked in, by the libgcrypt family. "
              "1.35 is built with -fcommon (GCC 10 default -fno-common breaks "
              "its MinGW x64 link); the x64 MinGW DLL is copied from "
              "libgpg-error6-0.dll to libgpg-error-0.dll where upstream "
              "names it that. See the module docstring for the pairing and "
              "why 1.47 is not carried.",
    )


RECIPES = {}
for _v in _SHA256:
    RECIPES["libgpg-error_%s" % _v] = _recipe(_v, linux=False)
    RECIPES["libgpg-error_%s_linux" % _v] = _recipe(_v, linux=True)

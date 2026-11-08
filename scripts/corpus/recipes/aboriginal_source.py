"""Target C libraries built from the Aboriginal / Firmware Linux SOURCE trees.

These are NOT the binaries Landley originally shipped. The original binary
tarballs (landley.net/aboriginal/downloads/old/binaries/..., and the
Firmware Linux 0.9.6 / Aboriginal 1.0.3 equivalents) are no longer
retrievable: landley.net redirects the binary paths to web.archive.org and
the Firmware 0.9.6 / Aboriginal 1.0.3 binaries returned HTTP 404 where they
were investigated. What is reachable is the build system itself, so each
recipe here runs the distribution's own, unmodified toolchain script
(./simple-cross-compiler.sh for Aboriginal, ./cross-compiler.sh for Firmware)
over the distribution's own component list, and harvests the target libc.a
that stage produces. The outputs are rebuilds from the stated scripts and
pinned components and cannot be assumed byte-identical to the historical
binaries (different host, different build time, host-dependent configure
results).

Pinned inputs (all sha256-verified by the corpus fetcher, a mismatch aborts
the build). The distribution tarballs come from landley.net; every component
comes from http://landley.net/aboriginal/mirror/, the mirror the
distributions themselves fall back to, whose files were checked to match the
SHA1 each distribution's download.sh records:
  Aboriginal 1.0.3   aboriginal-1.0.3.tar.bz2 987e931d4aecb1f71939efda32d36e81532eb4f94f237ce955dd3818b77aaf15
                     linux-3.0 (64b0228b...), uClibc-0.9.32 (23c133f7...),
                     binutils-2.17 (e2c33ce6...), gcc-core-4.2.1 (476fe4a6...)
  Aboriginal 1.4.4   aboriginal-1.4.4.tar.gz ae85cf840550853c413d33d151ca859dbaacc7dfc1b4181fa8b3fdee9d6e241f
                     linux-4.2 (1ba3e38b...), musl-1.1.12 (720b83c7..., the
                     same digest as the official release tarball used by
                     musl_1.1.12_*), binutils-397a64b3 (c7e0f0df...),
                     gcc-core-4.2.1 (476fe4a6...)
  Firmware 0.9.6     firmware-0.9.6.tar.bz2 d26e1a7306f8efb13f92667ea1dc3b81954b7805fd8dcdfb20746a3175f0b786
                     linux-2.6.29 (58a5ea16...), uClibc-0.9.30.1 (2d9769a0...),
                     binutils-2.17 (e2c33ce6...), gcc-core-4.1.2 (7be9c5df...),
                     gcc-g++-4.1.2 (0c06aa41...)
(full digests are in the Source entries below and in provenance.json).

Honest deviations from "just run build.sh", all in this recipe or the
helper script and none touching the distribution or component sources:
  * The toolchain stage runs inside a Docker container of the end-of-life
    host image named in HOST_IMAGE (ubuntu:14.04, GCC 4.8, pinned by the
    digest the CI log recorded), because GCC
    4.1.2 / 4.2.1 do not build with a current host compiler. The container's
    apt packages (build-essential, bzip2, patch, bison, flex, m4,
    gawk, file) are installed unpinned at build time and the image tag is not
    digest-pinned in the recipe; the digest actually used is printed by the
    docker pull in the build log.
  * Firmware Linux 0.9.6 only: a host-gcc wrapper in the container adds
    -D_POSIX_C_SOURCE=200112L to the single compile of uClibc's host tool
    extra/scripts/unifdef.c, because that file's own getline() conflicts with
    the host glibc's POSIX 2008 getline(); no source is edited.
  * The container gets a do-nothing makeinfo (texinfo is not installed), so
    the .info manuals of the binutils snapshot (Aboriginal 1.4.4), which do
    not build with the host's makeinfo, are skipped; no code is affected.
  * The distribution tarball is a pinned extra source, extracted by a build
    step, because the corpus extractor refuses its absolute-symlink
    etc/mtab; the recipe's main source is the zlib staging directory used by
    the sibling libc_harvest.py recipes and none of it is built or linked.
  * Only the cross-compiler stage is run, with NO_HOST_TOOLS=1 (skip the
    host-tools stage: busybox/toybox/distcc/e2fsprogs/squashfs helper
    programs for root-filesystem images), NO_CPLUSPLUS=1 (Aboriginal only;
    no g++ and no libstdc++), NO_STAGE_TARBALLS=1, SKIP_STRIP=1 (keep symbol
    tables). download.sh is not run; the
    pinned tarballs are copied into packages/ instead. All three are
    documented `config` switches of the distributions.
  * No busybox, toybox or root-filesystem binaries are added: the Linux
    userland reference set holds runtime libraries (libc, libgcc) and
    individual projects, and no tracker issue names the distribution
    userland.
  * libgcc is not re-harvested from these rebuilds (the GCC 4.2.1 / 4.1.2
    libgcc images already exist from the original archives).

The final step is the one the shipped-archive recipes in libc_harvest.py use:
the produced libc.a is linked by the host GCC with -nostdlib -no-pie
-Wl,-e,0 into an ELF container (uClibc whole-archive; musl with -u for every
global text symbol except __tlsdesc_*, see libc_harvest.py), entry address
zero, not runnable, dynamic libgcc_s. The host compiler in the artefact name
is that link driver, not the producer of the archived code. The producer
(GCC 4.2.1, or 4.1.2 for Firmware) is the compiler built by the same script
from the pinned source.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

# The end-of-life host the distributions were written against. Overridable
# through the environment only to try another host image in CI; a build that
# used an override is not the recorded build.
HOST_IMAGE = "ubuntu:14.04@sha256:64483f3496c1373bfd55348e88694d1c4d0c9b660dee6bfef5e12f43b9933b30"

_MIRROR = "http://landley.net/aboriginal/mirror/"


def _pkg(name, digest):
    return Source(url=_MIRROR + name, sha256=digest)


_LINUX_3_0 = _pkg("linux-3.0.tar.bz2", "64b0228b54ce39b0b2df086109a7b737cde58e3df4f779506ddcaccee90356a0")
_LINUX_4_2 = _pkg("linux-4.2.tar.gz", "1ba3e38b5cde8e4369800426991be78b1e0ce420aeb4404d1b477f912c1d668f")
_LINUX_2_6_29 = _pkg("linux-2.6.29.tar.bz2", "58a5ea16d499fe06f90fcbf1d687d1235d2cb9bc28bf979867bd3faadf38fc3f")
_UCLIBC_0_9_32 = _pkg("uClibc-0.9.32.tar.bz2", "23c133f788cbb55ef526793a25deeda8216e833fb93cc6fb9ab0b4b7991d8e28")
_UCLIBC_0_9_30_1 = _pkg("uClibc-0.9.30.1.tar.bz2", "2d9769a02c46cff73f56a076268192da1ce91c913e2e4e31c120be098f704c8c")
_MUSL_1_1_12 = _pkg("musl-1.1.12.tar.gz", "720b83c7e276b4b679c0bffe9509340d5f81fd601508e607e708177df0d31c0e")
_BINUTILS_2_17 = _pkg("binutils-2.17.tar.bz2", "e2c33ce6f23c9a366f109ced295626cb2f8bd6b2f08ff9df6dafb5448505a25e")
_BINUTILS_397 = _pkg("binutils-397a64b3.tar.bz2", "c7e0f0dfd2f53df76d2196b5bec0a2f0922c68c8719f9127efaf703c4f35939c")
_GCC_CORE_4_2_1 = _pkg("gcc-core-4.2.1.tar.bz2", "476fe4a6f10493fdb53070aa31515326975d2fdc38f2dce931526a528b9ca453")
_GCC_CORE_4_1_2 = _pkg("gcc-core-4.1.2.tar.bz2", "7be9c5df8000ae35d0928f0a254bfb5e8478cad5e5e57fd07820530c03b3711d")
_GCC_GXX_4_1_2 = _pkg("gcc-g++-4.1.2.tar.bz2", "0c06aa415f10679bc334f4627242e2b383387d0d44930da2922028dbd98fa2e2")

# (name tag, family, version, libc kind, distribution Source, upstream, stage,
#  stage output prefix, {placeholder: component Source}, producer note, licence)
_DISTRIBUTIONS = (
    ("uClibc_0.9.32_aboriginal1.0.3_src", "uClibc", "0.9.32-aboriginal1.0.3-src", "uclibc",
     Source(url="https://landley.net/aboriginal/downloads/aboriginal-1.0.3.tar.bz2",
            sha256="987e931d4aecb1f71939efda32d36e81532eb4f94f237ce955dd3818b77aaf15"),
     "simple-cross-compiler", "simple-cross-compiler",
     {"c_linux": _LINUX_3_0, "c_uclibc": _UCLIBC_0_9_32, "c_binutils": _BINUTILS_2_17,
      "c_gcc": _GCC_CORE_4_2_1},
     "Aboriginal Linux 1.0.3 (uClibc 0.9.32, GCC 4.2.1, binutils 2.17, Linux 3.0 headers)",
     "LGPL-2.1-or-later"),
    ("musl_1.1.12_aboriginal1.4.4_src", "musl", "1.1.12-aboriginal1.4.4-src", "musl",
     Source(url="https://landley.net/aboriginal/downloads/aboriginal-1.4.4.tar.gz",
            sha256="ae85cf840550853c413d33d151ca859dbaacc7dfc1b4181fa8b3fdee9d6e241f"),
     "simple-cross-compiler", "simple-cross-compiler",
     {"c_linux": _LINUX_4_2, "c_musl": _MUSL_1_1_12, "c_binutils": _BINUTILS_397,
      "c_gcc": _GCC_CORE_4_2_1},
     "Aboriginal Linux 1.4.4 (musl 1.1.12, GCC 4.2.1, binutils 397a64b3, Linux 4.2 headers)",
     "MIT"),
    ("uClibc_0.9.30.1_firmware0.9.6_src", "uClibc", "0.9.30.1-firmware0.9.6-src", "uclibc",
     Source(url="https://landley.net/aboriginal/downloads/old/firmware-0.9.6.tar.bz2",
            sha256="d26e1a7306f8efb13f92667ea1dc3b81954b7805fd8dcdfb20746a3175f0b786"),
     "cross-compiler", "cross-compiler",
     {"c_linux": _LINUX_2_6_29, "c_uclibc": _UCLIBC_0_9_30_1, "c_binutils": _BINUTILS_2_17,
      "c_gcc": _GCC_CORE_4_1_2, "c_gxx": _GCC_GXX_4_1_2},
     "Firmware Linux 0.9.6 (uClibc 0.9.30.1, GCC 4.1.2, binutils 2.17, Linux 2.6.29 headers)",
     "LGPL-2.1-or-later"),
)

_MUSL_SELECT = ("$(nm -g --defined-only libc.a 2>/dev/null | "
                "awk '$2 ~ /^[TW]$/ && $3 !~ /^__tlsdesc_/ {print \"-Wl,-u,\" $3}') libc.a")

RECIPES = {}
for (_tag, _family, _version, _libc, _dist, _stage, _outdir, _components,
     _producer, _license) in _DISTRIBUTIONS:
    for _arch, _cpu in (("x86", "i686"), ("x64", "x86_64")):
        _tree = "dist/build/%s-%s" % (_outdir, _cpu)
        _copy = " ".join("{%s}" % key for key in sorted(_components))
        if _libc == "uclibc":
            _link = ("{cc} {archflag} -nostdlib -no-pie -Wl,-e,0 "
                     "-Wl,--whole-archive libc.a -Wl,--no-whole-archive "
                     "-lgcc_s -o libc.elf")
            _how = "--whole-archive"
        else:
            _link = ("{cc} {archflag} -nostdlib -no-pie -Wl,-e,0 " + _MUSL_SELECT +
                     " -lgcc_s -o libc.elf")
            _how = "-u every global text symbol except __tlsdesc_*"
        RECIPES[_tag + "_" + _arch] = Recipe(
            family=_family, version=_version,
            source=Source(url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
                          sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"),
            extra_sources=dict(_components, c_dist=_dist),
            upstream="https://landley.net/aboriginal/; " +
                     ("https://uclibc.org/" if _libc == "uclibc" else "https://musl.libc.org/"),
            license=_license,
            build=[
                BuildStep("mkdir -p dist/packages"),
                BuildStep("tar -xf {c_dist} -C dist --strip-components=1"),
                BuildStep("cp " + _copy + " dist/packages/"),
                BuildStep('docker run --rm -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" '
                          '-v "$PWD/dist":/w '
                          '-v {repo}/scripts/corpus/exercisers/aboriginal_build.sh:/aboriginal_build.sh:ro '
                          '"${ABORIGINAL_HOST_IMAGE:-' + HOST_IMAGE + '}" '
                          "bash /aboriginal_build.sh " + _stage + " " + _cpu),
                BuildStep("find " + _tree + " -name 'libc.a' -print"),
                BuildStep("LIBC=$(find " + _tree + " -name libc.a | "
                          "awk '{print length($0), $0}' | sort -n | head -1 | cut -d' ' -f2-) && "
                          'test -n "$LIBC" && cp "$LIBC" libc.a'),
                BuildStep(_link),
            ],
            artifacts=[Artifact(path="libc.elf", component="libc.elf")],
            toolchains=["linux_" + _arch], requires=["tar", "nm", "docker"],
            drop_crt_glue=False,
            build_flags="Built from source by the " + _stage + ".sh of " + _producer +
                        " in a " + HOST_IMAGE + " container (NO_HOST_TOOLS=1 NO_CPLUSPLUS=1 "
                        "NO_STAGE_TARBALLS=1 SKIP_STRIP=1); libc.a linked on the host with -nostdlib "
                        "-no-pie -Wl,-e,0 " + _how + "; dynamic libgcc_s",
            notes="REBUILT FROM SOURCE, not the binary Landley shipped: " + _producer +
                  ". The distribution tarball and every component tarball are "
                  "pinned by sha256; the distribution's own " + _stage + ".sh "
                  "builds the cross toolchain and target libc inside a " + HOST_IMAGE +
                  " container (the era's host; GCC 4.x does not build with a "
                  "current compiler). The container's apt packages and the "
                  "image digest are not pinned. No patch is applied to the "
                  "distribution or to any component source by this recipe. "
                  "The host compiler in the artefact name only drives the "
                  "final link of libc.a into an ELF container; entry address "
                  "zero, no startup objects, dynamic libgcc_s, not runnable. "
                  "Runtime filter off because libc is the subject.",
        )

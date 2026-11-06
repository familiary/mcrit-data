"""GCC 4.2.1 runtime archives shipped by Aboriginal Linux 1.4.4.

The compiler is not rebuilt or run. A host linker resolves the original
archive members into an ELF executable with no startup objects and entry
address zero. This image is for disassembly, not execution. Host libc is
dynamic, so its bodies do not enter the family. The recorded host compiler
is the link driver; the harvested producer is GCC 4.2.1, confirmed by the
archive members' .comment sections. The runtime filter is disabled because
this family is the runtime being collected.

The digest-pinned zlib source is only an unpackable staging directory, as in
libstdcxx.py; its code is never built or linked. The actual subject is the
separately pinned toolchain_archive dependency. Only the two archives are
extracted, avoiding the distribution's absolute loader symlinks.

Measured coverage (SMDA 5.0.2; unique PicHashes, functions >=10 instructions):
  libgcc_4.1.2-uclibc0.9.30.1_gcc14_x64_libgcc.elf: 136 kept + 0 removed = 136 image functions; 95 >=10 instructions, 93 unique hashes.
  libgcc_4.1.2-uclibc0.9.30.1_gcc14_x86_libgcc.elf: 135 kept + 0 removed = 135 image functions; 98 >=10 instructions, 96 unique hashes.
  libgcc_4.2.1-aboriginal1.4.4_gcc14_x64_libgcc.elf: 145 kept + 0 removed = 145 image functions; 106 >=10 instructions, 101 unique hashes.
  libgcc_4.2.1-aboriginal1.4.4_gcc14_x86_libgcc.elf: 155 kept + 0 removed = 155 image functions; 115 >=10 instructions, 111 unique hashes.
  libgcc_4.1.2-uclibc0.9.30.1_gcc14_x64_libgcc.elf vs libgcc_4.2.1-aboriginal1.4.4_gcc14_x64_libgcc.elf: 11 shared; 82/90 unique to each.
  libgcc_4.1.2-uclibc0.9.30.1_gcc14_x86_libgcc.elf vs libgcc_4.2.1-aboriginal1.4.4_gcc14_x86_libgcc.elf: 4 shared; 92/107 unique to each.
  libgcc: every x86/x64 pairing has zero shared hashes.

Named link/glue survivors (name, PicHash, instruction count):
  libgcc_4.1.2-uclibc0.9.30.1_gcc14_x64_libgcc.elf: none.
  libgcc_4.1.2-uclibc0.9.30.1_gcc14_x86_libgcc.elf: none.
  libgcc_4.2.1-aboriginal1.4.4_gcc14_x64_libgcc.elf: none.
  libgcc_4.2.1-aboriginal1.4.4_gcc14_x86_libgcc.elf: none.
Unnamed import/PLT stubs remain where the host link needs them; these are
below the 10-instruction comparison floor. The runtime families deliberately
keep their own runtime code; no startup driver is added to those images.

Windows comparison: no MinGW or MSVC image is produced. These pinned
archives are ELF objects; libiptc and ntpd target Linux/POSIX interfaces.
There is therefore no Windows/Linux PicHash pair to report.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


RECIPES = {}
for _arch, _cpu, _digest in (
    ("x86", "i686", "4f016c9d7607839ffff28e70ebb46f384deabc5df17825c94e3a30388814ff25"),
    ("x64", "x86_64", "418b3710496e22904a5d8eb3361b629f8a49bc7232df1cfd9ff353323dc514bc"),
):
    RECIPES["libgcc_4.2.1_aboriginal1.4.4_" + _arch] = Recipe(
        family="libgcc", version="4.2.1-aboriginal1.4.4",
        upstream="https://gcc.gnu.org/; https://landley.net/aboriginal/",
        license="GPL-2.0-or-later with GCC runtime linking exception (GCC 4.2.1)",
        source=Source(url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
                      sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"),
        extra_sources={"toolchain_archive": Source(
            url="https://web.archive.org/web/20171205071925id_/http://landley.net/"
                "aboriginal/downloads/old/binaries/1.4.4/cross-compiler-" + _cpu + ".tar.gz",
            sha256=_digest)},
        build=[
            BuildStep("mkdir -p harvested"),
            BuildStep("tar -xzf {toolchain_archive} -C harvested --strip-components=1 "
                      "cross-compiler-" + _cpu + "/cc/lib/libgcc.a "
                      "cross-compiler-" + _cpu + "/cc/lib/libgcc_eh.a"),
            BuildStep("{cc} {archflag} -no-pie -nostartfiles -Wl,-e,0 "
                      "-Wl,--whole-archive harvested/cc/lib/libgcc.a "
                      "harvested/cc/lib/libgcc_eh.a -Wl,--no-whole-archive "
                      "-lc -o libgcc.elf"),
        ],
        artifacts=[Artifact(path="libgcc.elf", component="libgcc.elf")],
        toolchains=["linux_" + _arch], requires=["tar"], drop_crt_glue=False,
        build_flags="Prebuilt GCC 4.2.1 libgcc.a + libgcc_eh.a; host link only: "
                    "-no-pie -nostartfiles -Wl,-e,0 -Wl,--whole-archive; dynamic libc",
        notes="Harvested from Aboriginal Linux 1.4.4, not rebuilt. The GCC "
              "4.2.1 producer is confirmed by .comment. The recorded host "
              "compiler drives only the final link. Entry address zero, no "
              "startup, dynamic host libc; the image is not runnable. "
              "All members of libgcc.a and libgcc_eh.a are retained. "
              "The runtime filter is off because libgcc is the subject. "
              "zlib supplies only the staging directory; none of it is linked.",
    )

# The original uClibc.org distribution supplies the older GCC 4.1.2 axis.
for _arch, _cpu, _digest in (
    ("x86", "i686", "37172fec0d0b723bd51990662d5ccf98c0ba386427781a292a09ab7b212d432f"),
    ("x64", "x86_64", "38203f01f4dceff5c7128953b5ec50478cf0a1395a8c162223b150b53e338f41"),
):
    RECIPES["libgcc_4.1.2_uclibc0.9.30.1_" + _arch] = Recipe(
        family="libgcc", version="4.1.2-uclibc0.9.30.1",
        upstream="https://gcc.gnu.org/; https://uclibc.org/downloads/binaries/0.9.30.1/",
        license="GPL-2.0-or-later with GCC runtime linking exception (GCC 4.1.2)",
        source=Source(url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
                      sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"),
        extra_sources={"toolchain_archive": Source(
            url="https://uclibc.org/downloads/binaries/0.9.30.1/mini-native-" + _cpu + ".tar.bz2",
            sha256=_digest)},
        build=[
            BuildStep("mkdir -p harvested"),
            BuildStep("tar -xjf {toolchain_archive} -C harvested --strip-components=1 "
                      "mini-native-" + _cpu + "/usr/gcc/lib/libgcc.a "
                      "mini-native-" + _cpu + "/usr/gcc/lib/libgcc_eh.a"),
            BuildStep("{cc} {archflag} -no-pie -nostartfiles -Wl,-e,0 "
                      "-Wl,--whole-archive harvested/usr/gcc/lib/libgcc.a "
                      "harvested/usr/gcc/lib/libgcc_eh.a -Wl,--no-whole-archive "
                      "-lc -o libgcc.elf"),
        ],
        artifacts=[Artifact(path="libgcc.elf", component="libgcc.elf")],
        toolchains=["linux_" + _arch], requires=["tar"], drop_crt_glue=False,
        build_flags="Prebuilt GCC 4.1.2 libgcc.a + libgcc_eh.a; host link only: "
                    "-no-pie -nostartfiles -Wl,-e,0 -Wl,--whole-archive; dynamic libc",
        notes="Harvested from uClibc.org mini-native 0.9.30.1, not rebuilt. "
              "GCC 4.1.2 producer confirmed by .comment. The recorded host "
              "compiler drives only the final link. Entry zero, no startup, "
              "dynamic host libc; not runnable. All members of libgcc.a "
              "and libgcc_eh.a are retained. Runtime filter off because "
              "libgcc is the subject. zlib is only the staging directory.",
    )

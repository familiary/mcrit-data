"""Shipped uClibc 0.9.30.1 and musl 1.1.12 static bodies.

No libc code is rebuilt. The host compiler only drives a no-startup ELF
link; its version in provenance is the link driver, not the producer.
The digest-pinned zlib source is an unpackable staging directory, never
built or linked. Actual subjects are the pinned toolchain dependencies.
Only libc.a is extracted, leaving absolute distribution symlinks alone.

uClibc is linked whole. musl forces every defined global text symbol except
__tlsdesc_* through -u: the x64 archive contains tlsdesc.o but lacks its
hidden __tls_get_new dependency (the whole-archive error is recorded in the
README). Excluding these dynamic-loader-only symbols allows static libc
coverage without changing the archive or leaving unresolved relocations.
Compiler arithmetic dependencies use dynamic libgcc_s, keeping its bodies
out of the libc family. No startup driver is added; entry address is zero,
and these images are for disassembly, not execution.

Measured coverage (SMDA 5.0.2; unique PicHashes, functions >=10 instructions):
  uClibc_0.9.30.1_gcc14_x64_libc.elf: 1324 kept + 0 removed = 1324 image functions; 1017 >=10 instructions, 941 unique hashes.
  uClibc_0.9.30.1_gcc14_x86_libc.elf: 1316 kept + 0 removed = 1316 image functions; 1075 >=10 instructions, 1009 unique hashes.
  uClibc_0.9.33.2-aboriginal1.2.0_gcc14_x64_libc.elf: 1371 kept + 0 removed = 1371 image functions; 1034 >=10 instructions, 971 unique hashes.
  uClibc_0.9.33.2-aboriginal1.2.0_gcc14_x86_libc.elf: 1569 kept + 0 removed = 1569 image functions; 1169 >=10 instructions, 1094 unique hashes.
  uClibc_ng-1.0.39-bootlin2021.11-1_gcc14_x86_libc.elf: 2214 kept + 0 removed = 2214 image functions; 1554 >=10 instructions, 1496 unique hashes.
  uClibc_ng-1.0.39-bootlin2021.11-5_gcc14_x64_libc.elf: 2183 kept + 0 removed = 2183 image functions; 1394 >=10 instructions, 1284 unique hashes.
  uClibc_0.9.30.1_gcc14_x64_libc.elf vs uClibc_0.9.33.2-aboriginal1.2.0_gcc14_x64_libc.elf: 458 shared; 483/513 unique to each.
  uClibc_0.9.30.1_gcc14_x64_libc.elf vs uClibc_ng-1.0.39-bootlin2021.11-5_gcc14_x64_libc.elf: 15 shared; 926/1269 unique to each.
  uClibc_0.9.30.1_gcc14_x86_libc.elf vs uClibc_0.9.33.2-aboriginal1.2.0_gcc14_x86_libc.elf: 319 shared; 690/775 unique to each.
  uClibc_0.9.30.1_gcc14_x86_libc.elf vs uClibc_ng-1.0.39-bootlin2021.11-1_gcc14_x86_libc.elf: 29 shared; 980/1467 unique to each.
  uClibc_0.9.33.2-aboriginal1.2.0_gcc14_x64_libc.elf vs uClibc_ng-1.0.39-bootlin2021.11-5_gcc14_x64_libc.elf: 17 shared; 954/1267 unique to each.
  uClibc_0.9.33.2-aboriginal1.2.0_gcc14_x86_libc.elf vs uClibc_ng-1.0.39-bootlin2021.11-1_gcc14_x86_libc.elf: 32 shared; 1062/1464 unique to each.
  uClibc: every x86/x64 pairing has zero shared hashes.
  musl_1.1.12-aboriginal1.4.4_gcc14_x64_libc.elf: 1879 kept + 0 removed = 1879 image functions; 1150 >=10 instructions, 1080 unique hashes.
  musl_1.1.12-aboriginal1.4.4_gcc14_x86_libc.elf: 1848 kept + 0 removed = 1848 image functions; 1235 >=10 instructions, 1173 unique hashes.
  musl: every x86/x64 pairing has zero shared hashes.

Named link/glue survivors (name, PicHash, instruction count):
  uClibc_0.9.30.1_gcc14_x64_libc.elf: none.
  uClibc_0.9.30.1_gcc14_x86_libc.elf: none.
  uClibc_0.9.33.2-aboriginal1.2.0_gcc14_x64_libc.elf: none.
  uClibc_0.9.33.2-aboriginal1.2.0_gcc14_x86_libc.elf: none.
  uClibc_ng-1.0.39-bootlin2021.11-1_gcc14_x86_libc.elf: __x86.get_pc_thunk.bx 0x65ab80d640d961a1 (2); __x86.get_pc_thunk.dx 0x1872e6a0bbf1e5a2 (2); __x86.get_pc_thunk.cx 0x769f0aed4b5feefe (2); __x86.get_pc_thunk.si 0x99104660fd4df449 (2); __x86.get_pc_thunk.bp 0x7c99608cc56520ba (2); __x86.get_pc_thunk.ax 0x780400859718c5b0 (2); __x86.get_pc_thunk.di 0xd74c7b06352452d3 (2)
  uClibc_ng-1.0.39-bootlin2021.11-5_gcc14_x64_libc.elf: none.
  musl_1.1.12-aboriginal1.4.4_gcc14_x64_libc.elf: _init 0x9266c017df971c7c (1); _fini 0x9266c017df971c7c (1)
  musl_1.1.12-aboriginal1.4.4_gcc14_x86_libc.elf: _init 0x9266c017df971c7c (1); _fini 0x9266c017df971c7c (1)
Unnamed import/PLT stubs remain where the host link needs them; these are
below the 10-instruction comparison floor. The runtime families deliberately
keep their own runtime code; no startup driver is added to those images.

Windows comparison: no MinGW or MSVC image is produced. These pinned
archives are ELF objects; libiptc and ntpd target Linux/POSIX interfaces.
There is therefore no Windows/Linux PicHash pair to report.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


RECIPES = {}
for _family, _version, _arch, _cpu, _digest in (
    ("uClibc", "0.9.30.1", "x86", "i686", "37172fec0d0b723bd51990662d5ccf98c0ba386427781a292a09ab7b212d432f"),
    ("uClibc", "0.9.30.1", "x64", "x86_64", "38203f01f4dceff5c7128953b5ec50478cf0a1395a8c162223b150b53e338f41"),
    ("musl", "1.1.12-aboriginal1.4.4", "x86", "i686", "4f016c9d7607839ffff28e70ebb46f384deabc5df17825c94e3a30388814ff25"),
    ("musl", "1.1.12-aboriginal1.4.4", "x64", "x86_64", "418b3710496e22904a5d8eb3361b629f8a49bc7232df1cfd9ff353323dc514bc"),
):
    if _family == "uClibc":
        _url = "https://uclibc.org/downloads/binaries/0.9.30.1/mini-native-" + _cpu + ".tar.bz2"
        _member = "mini-native-" + _cpu + "/usr/lib/libc.a"
        _archive = "harvested/usr/lib/libc.a"
        _select = "-Wl,--whole-archive " + _archive + " -Wl,--no-whole-archive"
    else:
        _url = ("https://web.archive.org/web/20171205071925id_/http://landley.net/"
                "aboriginal/downloads/old/binaries/1.4.4/cross-compiler-" + _cpu + ".tar.gz")
        _member = "cross-compiler-" + _cpu + "/lib/libc.a"
        _archive = "harvested/lib/libc.a"
        _select = ("$(nm -g --defined-only " + _archive + " | "
                   "awk '$2 ~ /^[TW]$/ && $3 !~ /^__tlsdesc_/ {print \"-Wl,-u,\" $3}') " + _archive)
    RECIPES[_family + "_" + _version + "_" + _arch] = Recipe(
        family=_family, version=_version,
        source=Source(url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
                      sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"),
        extra_sources={"toolchain_archive": Source(url=_url, sha256=_digest)},
        upstream="https://uclibc.org/" if _family == "uClibc" else "https://musl.libc.org/; https://landley.net/aboriginal/",
        license="LGPL-2.1-or-later" if _family == "uClibc" else "MIT",
        build=[
            BuildStep("mkdir -p harvested"),
            BuildStep("tar -xf {toolchain_archive} -C harvested --strip-components=1 " + _member),
            BuildStep("{cc} {archflag} -nostdlib -no-pie -Wl,-e,0 " + _select + " -lgcc_s " + ("-lc " if _family == "musl" else "") + "-o libc.elf"),
        ],
        artifacts=[Artifact(path="libc.elf", component="libc.elf")],
        toolchains=["linux_" + _arch], requires=["tar", "nm"], drop_crt_glue=False,
        build_flags="Prebuilt static libc; host link only: -nostdlib -no-pie "
                    "-Wl,-e,0; " + ("--whole-archive" if _family == "uClibc" else "-u every global text symbol except __tlsdesc_*") + "; dynamic libgcc_s",
        notes="Shipped libc.a, not rebuilt. The host compiler in provenance "
              "only drives the final link. zlib supplies a staging directory "
              "and none of it is linked. No startup or driver, entry zero; "
              "not runnable. Dynamic libgcc_s keeps compiler arithmetic "
              "bodies out. The runtime filter is off because libc is the "
              "subject. " + ("uClibc.org mini-native 0.9.30.1, GCC 4.1.2 producer." if _family == "uClibc" else
              "Aboriginal Linux 1.4.4, musl 1.1.12, GCC 4.2.1 producer. "
              "All global text symbols except dynamic-loader __tlsdesc_* "
              "are forced from the original archive. Whole-archive x64 "
              "cannot resolve the hidden __tls_get_new from tlsdesc.o; "
              "no archive members are changed and no relocation is ignored."),
    )

# uClibc 0.9.33.2: distinct historical static archive from Aboriginal 1.2.0.
for _arch, _cpu, _digest in (
    ("x86", "i686", "8081a6a579df6afb144aae45af1b0f29171c5daeafee64b9b48f3b34b49d603f"),
    ("x64", "x86_64", "7e165cb77259e9266baac216f30974b55cb46434adf821e012b4db13c60cdd55"),
):
    RECIPES["uClibc_0.9.33.2_aboriginal1.2.0_" + _arch] = Recipe(
        family="uClibc", version="0.9.33.2-aboriginal1.2.0",
        source=Source(url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
                      sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"),
        extra_sources={"toolchain_archive": Source(
            url="https://web.archive.org/web/20171205071925id_/http://landley.net/"
                "aboriginal/downloads/old/binaries/1.2.0/cross-compiler-" + _cpu + ".tar.bz2",
            sha256=_digest)},
        upstream="https://uclibc.org/; https://landley.net/aboriginal/",
        license="LGPL-2.1-or-later",
        build=[
            BuildStep("mkdir -p harvested"),
            BuildStep("tar -xjf {toolchain_archive} -C harvested --strip-components=1 "
                      "cross-compiler-" + _cpu + "/lib/libc.a"),
            BuildStep("{cc} {archflag} -nostdlib -no-pie -Wl,-e,0 "
                      "-Wl,--whole-archive harvested/lib/libc.a "
                      "-Wl,--no-whole-archive -lgcc_s -o libc.elf"),
        ],
        artifacts=[Artifact(path="libc.elf", component="libc.elf")],
        toolchains=["linux_" + _arch], requires=["tar"], drop_crt_glue=False,
        build_flags="Prebuilt uClibc 0.9.33.2, Aboriginal 1.2.0; host link only: "
                    "-nostdlib -no-pie -Wl,-e,0 -Wl,--whole-archive; dynamic libgcc_s",
        notes="Original static libc.a from Aboriginal Linux 1.2.0, GCC 4.2.1 "
              "producer. Not rebuilt; the host compiler is only the link "
              "driver. All archive members retained. No startup or driver, "
              "entry zero; not runnable. Compiler arithmetic uses dynamic "
              "libgcc_s. Runtime filtering disabled because libc is the "
              "subject. zlib is an unpackable staging directory only.",
    )

# uClibc-ng stays in the uClibc family: it is the maintained continuation.
# Version macros in the shipped headers identify 1.0.39, not 1.0.34.
for _arch, _cpu, _release, _digest in (
    ("x86", "i686", "1", "d15cfe391474ea19e6a468c011955027581c6a16953380baf3c5718ad42fc45d"),
    ("x64", "x86_64", "5", "e68fd1b23f4a5c5132f2122e4012c17eb24e5179b2ff45bb793a27ac30dd454f"),
):
    _bootcpu = "x86-i686" if _arch == "x86" else "x86-64"
    _root = _bootcpu + "--uclibc--stable-2021.11-" + _release
    _lib = _cpu + "-buildroot-linux-uclibc/sysroot/usr/lib/libc.a"
    RECIPES["uClibc_ng_1.0.39_bootlin2021.11_" + _arch] = Recipe(
        family="uClibc", version="ng-1.0.39-bootlin2021.11-" + _release,
        source=Source(url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
                      sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"),
        extra_sources={"toolchain_archive": Source(
            url="https://toolchains.bootlin.com/downloads/releases/toolchains/" + _bootcpu + "/tarballs/" + _root + ".tar.bz2",
            sha256=_digest)},
        upstream="https://uclibc-ng.org/; https://toolchains.bootlin.com/",
        license="LGPL-2.1-or-later",
        build=[
            BuildStep("mkdir -p harvested"),
            BuildStep("tar -xjf {toolchain_archive} -C harvested --strip-components=1 " + _root + "/" + _lib),
            BuildStep("{cc} {archflag} -nostdlib -no-pie -Wl,-e,0 "
                      "-Wl,--whole-archive harvested/" + _lib + " "
                      "-Wl,--no-whole-archive -Wl,--copy-dt-needed-entries "
                      "-lgcc_s -lc -o libc.elf"),
        ],
        artifacts=[Artifact(path="libc.elf", component="libc.elf")],
        toolchains=["linux_" + _arch], requires=["tar"], drop_crt_glue=False,
        build_flags="Prebuilt uClibc-ng 1.0.39, Bootlin stable-2021.11-" + _release + "; host link only: "
                    "-nostdlib -no-pie -Wl,-e,0 -Wl,--whole-archive "
                    "-Wl,--copy-dt-needed-entries; dynamic libgcc_s and libc",
        notes="Shipped static uClibc-ng libc.a, maintained continuation of "
              "uClibc in the same family. Shipped header version macros "
              "identify 1.0.39. All archive members retained. The host "
              "compiler only drives the final link; no code is rebuilt. "
              "Dynamic host libc and libgcc_s resolve external references "
              "without including their bodies; --copy-dt-needed-entries "
              "resolves the TLS resolver from the dynamic loader. No startup, "
              "entry zero; not runnable. Runtime filter off because libc "
              "is the subject. zlib is only a staging directory.",
    )

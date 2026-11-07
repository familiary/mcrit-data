"""chokepoint/azazel (mcrit-data issue #55) - LD_PRELOAD hook set, ELF x86/x64.

A userland rootkit built as a shared object and installed by writing its path
into `/etc/ld.so.preload`, so that the dynamic linker interposes its versions
of `open`, `stat`, `execve`, `unlink`, the `readdir` family, the PAM entry
points and `pcap_loop` ahead of libc's. Chronicle's Winnti-for-Linux
reporting, as MITRE records it under S0430, describes a modified copy of this
project shipped as `libxselinux.so` - one character off upstream's own
`-Wl,-soname,libselinux.so`.

This is the corpus's first ELF artefact that is a real implant rather than a
portable library compiled for a second platform, and it is the one family
here where the standing ELF advice has to be inverted.

**No `-fvisibility=hidden`, deliberately.** Every other `*_linux.py` recipe
passes it, and `scripts/corpus/README.md` argues at length for it: an ELF
shared object exports every global symbol by default, so a header-only
library's own instantiations get exported and called through `.plt` stubs,
which is how `StringObfuscatorCT` x64 came out at 385 functions with 271
unnamed stubs. None of that reasoning applies to an interposition library.
Azazel's exported symbols *are* the artefact: `open`, `__xstat`,
`pam_authenticate` and the rest have to be exported, under exactly those
names, or `ld.so.preload` has nothing to interpose and the thing is not
azazel any more. Hiding them would produce a shape that upstream cannot
build and that no sample resembles. The cost is paid and measured instead -
see the counts below.

**`make config` is not run, and does not need to be.** The `config` target
is `python config.py > const.h`, and `config.py` is Python 2 (bare `print`
statements), which this host has no interpreter for. It also does not have to
run: upstream *commits* `const.h`, and the committed file is config.py's
output for the defaults in its own "Change everything in this box" block.
That was verified rather than assumed - `config.py`'s obfuscation is
`chr(c ^ 0xfe)` per byte, and decoding the committed `syscall_table` under it
returns `config.py`'s 24 names in its exact order (`accept`, `access`,
`execve`, `link`, `__lxstat`, ... `pcap_loop`), with `BLIND_LOGIN` decoding
to `rootme` and `PASSPHRASE` to `Hello NSA`. So the artefact's string table
is upstream's default configuration, not one chosen here, and nothing about
the build depends on an interpreter version.

**Three command-line fixes, no source patch.** All three are flags or
defines, which is what this repository permits; the tree is untouched.

* `-fcommon`. `azazel.h:31` declares `void *syscall_list[SYSCALL_SIZE];` in a
  header with no `extern`, i.e. a tentative definition in every translation
  unit that includes it. That linked under GCC 9 and earlier, whose default
  was `-fcommon`; GCC 10 made `-fno-common` the default, and the link now
  fails with `multiple definition of 'syscall_list'` from `pam.o` and
  `pcap.o` against `azazel.o`. `-fcommon` restores the behaviour the code was
  written against.
* `-D_STAT_VER=1` on x64 and `-D_STAT_VER=3` on x86. glibc 2.33 removed the
  `__xstat`/`__lxstat` interface and the `_STAT_VER` macro with it, because
  `stat()` is no longer routed through those entry points; azazel hooks them
  and passes `_STAT_VER`, so five call sites in `azazel.c` fail to compile.
  The values are glibc's own `_STAT_VER_LINUX` for each ABI - 1 for x86-64,
  3 for i386 - so the define reproduces what the header supplied when this
  code was current, rather than inventing a number.
* The compile and link are spelled out rather than invoked through `make`,
  because `Makefile:17` ends the `libselinux.so` rule with `strip
  libselinux.so`. A stripped report is treated as a build failure by this
  pipeline, and the strip is inside the makefile where no environment
  variable reaches. The two command lines below are the makefile's own
  (`Makefile:15-16`), minus that third line.

**Upstream never links `-lcrypto`, and the artefact shows it.** `crypthook.c`
includes `<openssl/evp.h>`, `<openssl/sha.h>` and `<openssl/rand.h>` and
calls `EVP_EncryptInit_ex`, `EVP_DecryptUpdate`, `EVP_CIPHER_CTX_new` and
friends, but `Makefile:4` is `LDFLAGS += -lc -ldl -lpam -lutil` with no
`-lcrypto`. A shared object is allowed to link with symbols undefined, so
this builds, and the committed artefact carries 8 undefined `EVP_*`
references. That is upstream's shape, not a fault introduced here, and it is
recorded because an analyst reading the imports should know the OpenSSL
dependency is unresolved in upstream's own build. OpenSSL *headers* are still
needed to compile, and libpam headers to compile `pam.c`; `pcap/pcap.h` is
needed for `pcap.c` and is architecture-independent, and no `-lpcap` is
linked either.

**No optimization.** `Makefile:3` is `CFLAGS += -Wall` and the compile line
adds `-g`; there is no `-O` anywhere, so this builds at `-O0`, which is what
`build_flags` records. One warning survives and is left alone:
`azazel.c:613` calls `wait` without including `<sys/wait.h>`.

**Measured, and why `min_named_ratio` is lowered.** Both architectures
report 176 functions and 56 of them named, and those 56 are the project's
own code, summing exactly over the x64 objects: `azazel.o` 38, `pam.o` 7,
`crypthook.o` 6, `pcap.o` 3, `xor.o` 2. 30 are exported on both, which is
the hook set. Everything unnamed is a `.plt` stub, the cost of not passing
`-fvisibility=hidden`.

What differs between the two is only how long those stubs are, and it is
enough to move the symbol gate from trivially passing to failing:

    x86   >=3 instructions:  56 functions,  56 named  (100%)
    x64   >=3 instructions: 114 functions,  55 named   (48%)

On i386 every stub lands below the gate's three-instruction cut and is not
counted; on x86-64 the stubs are three instructions or more, so 59 of them
are. The *named* content of the two artefacts is identical - same 56
functions, all azazel's - and the ratio differs for a reason that is a
property of the two ABIs' PLT shapes rather than of this build.

So `min_named_ratio=0.45` is set, below the 0.48 measured on x64. This is
the knob's intended use rather than a way past a broken build, and the x86
artefact is the control that shows it: the same source and the same flags
score 1.00 there. The alternative ways to raise the number were both
rejected on purpose - `-fvisibility=hidden` would unexport the hooks and
destroy the artefact, and a `-Wl,--version-script` keeping only the 30 hooks
global would be a link line upstream does not have, giving a shape that no
real sample (all built with upstream's own link) would match.

**This family is the hardest test of the glue filter in the corpus**, and
that is the reason it is worth having. Most of its functions are *named after
the libc and PAM entry points they replace* - `open`, `stat`, `stat64`,
`execve`, `unlink`, `fopen`, `getpwnam_r`, `pam_authenticate`. The filter in
`corpus/baseline.py` drops a function only when its symbol **and** its
PicHash match the probe, which is exactly the rule that has to hold here: a
project shipping its own `open` must keep it. The drop count is recorded in
provenance so the mechanism can be audited rather than trusted.

**Overlap with Medusa (#40) is not yet measurable.** Issue #55 asks for this
family to be decided together with #40, which shares 21 symbol names with it
(`__lxstat`, `__xstat`, `access`, `execve`, `fopen`, `getpwnam_r`, `lstat`,
`open`, `opendir`, the four `pam_*`, `pcap_loop`, `stat`, `unlink`,
`unlinkat` and their `*64` variants). Medusa is a kernel module and is not
built here, so no cross-family PicHash between the two exists yet to measure.
When Medusa arrives, those 21 names are where leakage would show up, and the
`validate --deep` rule that fails on one symbol repeated across three
families is the gate that would catch it.

`crypthook.c` is vendored from chokepoint/CryptHook - 6 functions in the
object, of which `gen_key`, `encrypt_data`, `decrypt_data`, `crypt_read` and
`crypt_write` are its own. At that size it is below this corpus's
eight-function floor as a family of its own, so it stays here and is recorded
in `notes` rather than split out.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# glibc's own _STAT_VER_LINUX: 3 on i386, 1 on x86-64. Spelled as a shell
# conditional on {bitness} because the two ABIs need different values and one
# command line serves both toolchains.
_STAT_VER = '$([ {bitness} = 32 ] && echo 3 || echo 1)'

# Makefile:15, plus -fcommon and -D_STAT_VER. The file list is upstream's.
_COMPILE = ("{cc} {archflag} -D_STAT_VER=%s -fcommon -Wall -fPIC -g "
            "-c azazel.c pam.c xor.c crypthook.c pcap.c" % _STAT_VER)

# Makefile:16 verbatim, including the object order and the soname upstream
# chose. Makefile:17's `strip libselinux.so` is the line deliberately not run.
_LINK = ("{cc} {archflag} -fPIC -shared -Wl,-soname,libselinux.so "
         "azazel.o xor.o pam.o crypthook.o pcap.o "
         "-lc -ldl -lpam -lutil -o libselinux.so")


RECIPES = {
    "Azazel_2020-07-14": Recipe(
        family="Azazel",
        version="2020-07-14",
        upstream="https://github.com/chokepoint/azazel",
        license="GPL-2.0, full text in LICENSE",
        source=Source(git_url="https://github.com/chokepoint/azazel.git",
                      git_ref="a41fbb5256f4368a54313f7ff4e88af973ebeb08"),
        build=[BuildStep(_COMPILE), BuildStep(_LINK)],
        artifacts=[Artifact(path="libselinux.so",
                            component="libselinux.so")],
        toolchains=["linux_x86", "linux_x64"],
        # 0.48 is what x64 measures over functions of three instructions or
        # more; x86 measures 1.00 on the same source and flags. Both report
        # the same 56 named functions, all of them this project's. What
        # dilutes the x64 number is .plt stubs that are three instructions
        # long on that ABI and shorter on i386, and they exist because the
        # hooks have to stay exported. See the docstring: the two ways to
        # raise it both change the artefact into something upstream does not
        # build.
        min_named_ratio=0.45,
        build_flags="gcc -O0 (upstream sets no -O: Makefile CFLAGS is only "
                    "-Wall, compile adds -g) -fPIC -shared "
                    "-Wl,-soname,libselinux.so, linked -lc -ldl -lpam "
                    "-lutil; this recipe adds -fcommon (GCC 10 made "
                    "-fno-common the default and azazel.h:31 is a tentative "
                    "definition in a header) and -D_STAT_VER=3 on x86 / 1 on "
                    "x64 (glibc 2.33 removed __xstat and the _STAT_VER "
                    "macro); upstream's trailing `strip libselinux.so` is "
                    "not run",
        notes="An LD_PRELOAD userland rootkit, linked as a shared object and "
              "installed by writing its path into /etc/ld.so.preload. "
              "Chronicle's Winnti-for-Linux reporting, via MITRE S0430, "
              "describes a modified copy shipped as libxselinux.so, one "
              "character off upstream's own -Wl,-soname,libselinux.so. "
              "Built WITHOUT -fvisibility=hidden, unlike every other ELF "
              "recipe here: an interposition library's exports are the "
              "artefact, and hiding open/__xstat/pam_authenticate would "
              "produce a shape upstream cannot build and no sample "
              "resembles; the unnamed .plt stubs in the reports are the "
              "cost. 56 symbol-carrying functions on x64 and 60 on x86, 30 "
              "exported on both, the x64 total summing over the objects as "
              "azazel 38, pam 7, crypthook 6, pcap 3, xor 2. make config is "
              "not run: upstream commits const.h, and it was verified to be "
              "config.py's own default output by decoding its syscall_table "
              "under config.py's xor (c ^ 0xfe), which returns the 24 names "
              "in config.py's order, so the string table is upstream's "
              "default configuration rather than one chosen here. Most of "
              "this family's functions are named after the libc and PAM "
              "entry points they hook, so it is the hardest test in the "
              "corpus of the rule that baseline.py drops a function only on "
              "symbol AND PicHash; the drop count here should be read with "
              "that in mind. crypthook.c is vendored from "
              "chokepoint/CryptHook (6 functions in the object) and stays "
              "under this family, being below the eight-function floor on "
              "its own. Upstream links no -lcrypto despite crypthook.c "
              "calling EVP_*, so the artefact carries 8 undefined OpenSSL "
              "references - upstream's shape, not an error here. Issue #55 "
              "asks that this be decided with Medusa (#40), which shares 21 "
              "symbol names with it; Medusa is a kernel module and is not "
              "built, so that overlap is not yet measurable.",
    ),
}

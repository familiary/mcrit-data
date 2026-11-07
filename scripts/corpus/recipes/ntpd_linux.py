"""The legitimate ntpd daemon, early and current releases, Linux ELF.

Issue #57 names no version. 4.2.0 and 4.2.2 are early references (4.2.2 dates from 2006) and 4.2.8p18
is the current stable reference; neither claims to be the unidentified
Turla host version. Matches also identify clean installations and are not
indicators of compromise. Only ntpd is collected, including the libntp,
libparse and bundled support objects actually reached by its upstream link.
No ntpq, ntpdc, ntpdate, sntp or standalone libntp image is collected.

The default supported reference-clock set is retained. External OpenSSL
and SNMP integration are disabled; glibc and libm stay dynamic. GCC 14
needs -fcommon for these releases, and warning-level flags for legacy
configure probes (notably pthread_detach(NULL)). No source is changed for
4.2.2 and 4.2.8p18.

ntpd 4.2.0 needs a build-tree patch applied by this recipe (maintainer
decision; nothing patched is committed). GCC rejects, with no flag or
older compiler able to avoid it (-std=gnu89, -fcommon, -Wno-error and
-fpermissive do not affect it, and only gcc-13 is installed):
  include/ntp_stdlib.h:138:23: error: array type has incomplete element type 'struct clktype'
  include/ntpd.h:230:24: error: array type has incomplete element type 'struct ctl_trap'
Both are extern declarations of arrays of a type that is only forward
declared; every user already sees the complete definition (clocktypes.c
includes ntp_refclock.h, ntp_control.c and ntp_request.c include
ntp_control.h, which also carries a function-local extern for ctl_trap).
The recipe's first build step deletes the four declaration lines:
  --- include/ntp_stdlib.h
  -struct clktype;
  -extern struct clktype clktypes[];
  --- include/ntpd.h
  -struct ctl_trap;
  -extern struct ctl_trap ctl_trap[];
Code generation is unchanged; only declarations were removed. The 4.2.0
image is NOT byte-identical to a build of unmodified upstream source.
It is built with the host GCC 13.3.0 (the only GCC installed), so its
artefact names carry gcc13, unlike the gcc14 4.2.2/4.2.8p18 images.

Measured coverage (SMDA 5.0.2; unique PicHashes, functions >=10 instructions):
  ntpd_4.2.0_gcc13_x64_ntpd: 743 kept + 6 removed = 749 image functions; 397 >=10 instructions, 388 unique hashes.
  ntpd_4.2.0_gcc13_x86_ntpd: 753 kept + 5 removed = 758 image functions; 439 >=10 instructions, 439 unique hashes.
  ntpd_4.2.2_gcc14_x64_ntpd: 635 kept + 6 removed = 641 image functions; 424 >=10 instructions, 416 unique hashes.
  ntpd_4.2.2_gcc14_x86_ntpd: 766 kept + 7 removed = 773 image functions; 471 >=10 instructions, 471 unique hashes.
  ntpd_4.2.8p18_gcc14_x64_ntpd: 1173 kept + 7 removed = 1180 image functions; 945 >=10 instructions, 894 unique hashes.
  ntpd_4.2.8p18_gcc14_x86_ntpd: 1638 kept + 10 removed = 1648 image functions; 1194 >=10 instructions, 1184 unique hashes.
  ntpd_4.2.2_gcc14_x64_ntpd vs ntpd_4.2.8p18_gcc14_x64_ntpd: 0 shared; 416/894 unique to each.
  ntpd_4.2.2_gcc14_x86_ntpd vs ntpd_4.2.8p18_gcc14_x86_ntpd: 0 shared; 471/1184 unique to each.
  ntpd_4.2.0_gcc13_x64_ntpd vs ntpd_4.2.2_gcc14_x64_ntpd: 3 shared; 385/413 unique to each.
  ntpd_4.2.0_gcc13_x86_ntpd vs ntpd_4.2.2_gcc14_x86_ntpd: 6 shared; 433/465 unique to each.
  ntpd_4.2.0 vs ntpd_4.2.8p18: 0 shared on both x86 and x64 (388/894 x64, 439/1184 x86 unique).
  ntpd: every x86/x64 pairing has zero shared hashes.

Named link/glue survivors (name, PicHash, instruction count):
  ntpd_4.2.0_gcc13_x64_ntpd: none.
  ntpd_4.2.0_gcc13_x86_ntpd: _init 0xee8b93b4cd8240e7 (11); deregister_tm_clones 0x2cd9c47f861e2e10 (18); register_tm_clones 0xda6aa6ced1520f3a (26); __do_global_dtors_aux 0x09d11edd5fb96cae (21); __x86.get_pc_thunk.bp 0x7c99608cc56520ba (2); __x86.get_pc_thunk.cx 0x769f0aed4b5feefe (2); __x86.get_pc_thunk.si 0x99104660fd4df449 (2); __stack_chk_fail_local 0x5f3c441f2bf216b7 (6)
  ntpd_4.2.2_gcc14_x64_ntpd: none.
  ntpd_4.2.2_gcc14_x86_ntpd: _init 0xe9d2d8bf3378803b (11); deregister_tm_clones 0x12369fb1d8879bc7 (18); register_tm_clones 0x767546a7ded85494 (26); __do_global_dtors_aux 0x9d1d5734edf2f52c (21); __x86.get_pc_thunk.bp 0x7c99608cc56520ba (2)
  ntpd_4.2.8p18_gcc14_x64_ntpd: none.
  ntpd_4.2.8p18_gcc14_x86_ntpd: _init 0xcda2e48594dcdfa5 (11); deregister_tm_clones 0xebaced83d3124adc (18); register_tm_clones 0xaff5468dfb219b53 (26); __do_global_dtors_aux 0xb7cf53e7ef98f572 (21); __x86.get_pc_thunk.bp 0x7c99608cc56520ba (2); __stack_chk_fail_local 0x16cf06611a442299 (5)
Unnamed import/PLT stubs remain where the host link needs them; these are
below the 10-instruction comparison floor. The runtime families deliberately
keep their own runtime code; no startup driver is added to those images.

Windows comparison: no MinGW or MSVC image is produced. These pinned
archives are ELF objects; libiptc and ntpd target Linux/POSIX interfaces.
There is therefore no Windows/Linux PicHash pair to report.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_FLAGS = "-O2 {archflag} -fcommon -fvisibility=hidden -Wno-error=implicit-function-declaration -Wno-error=incompatible-pointer-types -Wno-error=int-conversion"
RECIPES = {}
# 4.2.0 only: GCC rejects the two incomplete-element-type array externs
# ("array type has incomplete element type"). Both are deleted by the recipe
# at build time (never committed to the repo); this image is NOT
# byte-identical to a build of unmodified upstream source.
_PATCH_4_2_0 = (
    "sed -i -e '/^struct clktype;$/d' -e '/^extern struct clktype clktypes\\[\\];$/d' include/ntp_stdlib.h"
    " && sed -i -e '/^struct ctl_trap;$/d' -e '/^extern struct ctl_trap ctl_trap\\[\\];$/d' include/ntpd.h"
)
for _version, _url, _digest in (
    ("4.2.0", "https://archive.ntp.org/ntp4/4.2.0/ntp-4.2.0.tar.gz", "da784d5c0363d4f708a25f3aad23ba9a3486aafd464444d2aa6a9f8d29213f25"),
    ("4.2.2", "https://archive.ntp.org/ntp4/4.2.2/ntp-4.2.2.tar.gz", "fb392fa5f1a753043981e661b09c6d0249050ff903078ed215a568952d76befc"),
    ("4.2.8p18", "https://archive.ntp.org/ntp4/ntp-4.2.8p18.tar.gz", "cf84c5f3fb1a295284942624d823fffa634144e096cfc4f9969ac98ef5f468e5"),
):
    RECIPES["ntpd_" + _version + "_linux"] = Recipe(
        family="ntpd", version=_version,
        source=Source(url=_url, sha256=_digest),
        upstream="https://www.ntp.org/; https://github.com/ntp-project/ntp",
        license="NTP licence (upstream COPYRIGHT); bundled support licences in source",
        build=([BuildStep(_PATCH_4_2_0)] if _version == "4.2.0" else []) + [
            BuildStep("./configure --host={host} --without-crypto --without-ntpsnmpd"
                      + (" --with-yielding-select=yes" if _version == "4.2.8p18" else ""),
                      env={"CC": "{cc} {archflag}", "CFLAGS": _FLAGS}),
            BuildStep("make -C libntp -j2"),
            BuildStep("make -C libparse -j2"),
            BuildStep("make -C ntpd -j2"),
        ],
        artifacts=[Artifact(path="ntpd/ntpd", component="ntpd")],
        toolchains=["linux_x86", "linux_x64"], requires=["make"],
        build_flags=_FLAGS.replace("{archflag}", "-m32/-m64") + " --without-crypto --without-ntpsnmpd; default supported reference clocks"
                    + ("; --with-yielding-select=yes" if _version == "4.2.8p18" else "")
                    + ("; recipe sed deletes four incomplete-array extern declarations in include/ntp_stdlib.h and include/ntpd.h (NOT byte-identical to unmodified upstream)" if _version == "4.2.0" else ""),
        notes=("" if _version != "4.2.0" else
              "Build-tree patch applied by the recipe, not committed: "
              "the declaration lines 'struct clktype;' and 'extern struct "
              "clktype clktypes[];' are deleted from include/ntp_stdlib.h, "
              "and 'struct ctl_trap;' and 'extern struct ctl_trap "
              "ctl_trap[];' from include/ntpd.h, because GCC rejects arrays "
              "of incomplete element type. This image is NOT byte-identical "
              "to a build of unmodified upstream. ") +
              "Legitimate daemon baseline: matches clean ntpd installations "
              "and is not an indicator of compromise. Issue #57 supplies "
              "no version; these are chosen era references, not claims "
              "about Turla's build. Only ntpd is harvested, including the "
              "libntp, libparse and bundled support objects its link reaches. "
              "Default supported clocks retained. OpenSSL and SNMP "
              "integration disabled. System libc and libm are dynamic. "
              "-fcommon and warning flags accommodate legacy configure "
              "probes on GCC 14" + (" without changing upstream source." if _version != "4.2.0" else "; flags only, apart from the patch described above."),
    )

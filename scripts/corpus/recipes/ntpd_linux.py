"""The legitimate ntpd daemon, early and current releases, Linux ELF.

Issue #57 names no version. 4.2.2 is an early 2006 reference and 4.2.8p18
is the current stable reference; neither claims to be the unidentified
Turla host version. Matches also identify clean installations and are not
indicators of compromise. Only ntpd is collected, including the libntp,
libparse and bundled support objects actually reached by its upstream link.
No ntpq, ntpdc, ntpdate, sntp or standalone libntp image is collected.

The default supported reference-clock set is retained. External OpenSSL
and SNMP integration are disabled; glibc and libm stay dynamic. GCC 14
needs -fcommon for these releases, and warning-level flags for legacy
configure probes (notably pthread_detach(NULL)). No source is changed.

Measured coverage (SMDA 5.0.2; unique PicHashes, functions >=10 instructions):
  ntpd_4.2.2_gcc14_x64_ntpd: 635 kept + 6 removed = 641 image functions; 424 >=10 instructions, 416 unique hashes.
  ntpd_4.2.2_gcc14_x86_ntpd: 766 kept + 7 removed = 773 image functions; 471 >=10 instructions, 471 unique hashes.
  ntpd_4.2.8p18_gcc14_x64_ntpd: 1173 kept + 7 removed = 1180 image functions; 945 >=10 instructions, 894 unique hashes.
  ntpd_4.2.8p18_gcc14_x86_ntpd: 1638 kept + 10 removed = 1648 image functions; 1194 >=10 instructions, 1184 unique hashes.
  ntpd_4.2.2_gcc14_x64_ntpd vs ntpd_4.2.8p18_gcc14_x64_ntpd: 0 shared; 416/894 unique to each.
  ntpd_4.2.2_gcc14_x86_ntpd vs ntpd_4.2.8p18_gcc14_x86_ntpd: 0 shared; 471/1184 unique to each.
  ntpd: every x86/x64 pairing has zero shared hashes.

Named link/glue survivors (name, PicHash, instruction count):
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
for _version, _url, _digest in (
    ("4.2.2", "https://archive.ntp.org/ntp4/4.2.2/ntp-4.2.2.tar.gz", "fb392fa5f1a753043981e661b09c6d0249050ff903078ed215a568952d76befc"),
    ("4.2.8p18", "https://archive.ntp.org/ntp4/ntp-4.2.8p18.tar.gz", "cf84c5f3fb1a295284942624d823fffa634144e096cfc4f9969ac98ef5f468e5"),
):
    RECIPES["ntpd_" + _version + "_linux"] = Recipe(
        family="ntpd", version=_version,
        source=Source(url=_url, sha256=_digest),
        upstream="https://www.ntp.org/; https://github.com/ntp-project/ntp",
        license="NTP licence (upstream COPYRIGHT); bundled support licences in source",
        build=[
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
                    + ("; --with-yielding-select=yes" if _version == "4.2.8p18" else ""),
        notes="Legitimate daemon baseline: matches clean ntpd installations "
              "and is not an indicator of compromise. Issue #57 supplies "
              "no version; these are chosen era references, not claims "
              "about Turla's build. Only ntpd is harvested, including the "
              "libntp, libparse and bundled support objects its link reaches. "
              "Default supported clocks retained. OpenSSL and SNMP "
              "integration disabled. System libc and libm are dynamic. "
              "-fcommon and warning flags accommodate legacy configure "
              "probes on GCC 14 without changing upstream source.",
    )

"""libiptc from iptables, Linux x86/x64.

Issue #43 names no version; 1.8.11 is a freely chosen recent legacy API
reference. The IPv4 and IPv6 archives are linked whole into one shared
image, preserving the internal API without including the iptables CLI,
extensions, libxtables, libmnl or libnftnl. This image is a corpus link
construction, rather than an upstream-distributed shared library.

The source is unmodified. Hidden visibility and -Bsymbolic keep internal
calls direct; libc remains dynamic. The nft backend is disabled.

Measured coverage (SMDA 5.0.2; unique PicHashes, functions >=10 instructions):
  libiptc_1.8.11_gcc14_x64_libiptc.so: 104 kept + 5 removed = 109 image functions; 75 >=10 instructions, 53 unique hashes.
  libiptc_1.8.11_gcc14_x86_libiptc.so: 131 kept + 7 removed = 138 image functions; 81 >=10 instructions, 80 unique hashes.
  libiptc: every x86/x64 pairing has zero shared hashes.

Named link/glue survivors (name, PicHash, instruction count):
  libiptc_1.8.11_gcc14_x64_libiptc.so: none.
  libiptc_1.8.11_gcc14_x86_libiptc.so: _init 0xba9a54537df0654f (11); deregister_tm_clones 0x5d8bc203315df395 (18); register_tm_clones 0xc0d81fbf84d9138d (26); __do_global_dtors_aux 0x7e9bea9af275ea50 (21); __x86.get_pc_thunk.bp 0x7c99608cc56520ba (2); _fini 0x9d983e6b98c1b0fb (7)
Unnamed import/PLT stubs remain where the host link needs them; these are
below the 10-instruction comparison floor. The runtime families deliberately
keep their own runtime code; no startup driver is added to those images.

Windows comparison: no MinGW or MSVC image is produced. These pinned
archives are ELF objects; libiptc and ntpd target Linux/POSIX interfaces.
There is therefore no Windows/Linux PicHash pair to report.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


RECIPES = {
    "libiptc_1.8.11_linux": Recipe(
        family="libiptc",
        version="1.8.11",
        source=Source(
            url="https://www.netfilter.org/projects/iptables/files/iptables-1.8.11.tar.xz",
            sha256="d87303d55ef8c92bcad4dd3f978b26d272013642b029425775f5bad1009fe7b2",
        ),
        upstream="https://git.netfilter.org/iptables/",
        license="GPL-2.0-or-later",
        build=[
            BuildStep(
                "./configure --host={host} --disable-nftables --disable-shared "
                "--enable-static",
                env={"CC": "{cc} {archflag}",
                     "CFLAGS": "-O2 {archflag} -fPIC -fvisibility=hidden"},
            ),
            BuildStep("make -C libiptc -j2"),
            BuildStep(
                "{cc} {archflag} -shared -Wl,-Bsymbolic -Wl,--whole-archive "
                "libiptc/.libs/libip4tc.a libiptc/.libs/libip6tc.a "
                "-Wl,--no-whole-archive -o libiptc.so"
            ),
        ],
        artifacts=[Artifact(path="libiptc.so", component="libiptc.so")],
        toolchains=["linux_x86", "linux_x64"],
        requires=["make"],
        build_flags="-O2 -fPIC -fvisibility=hidden -shared -Wl,-Bsymbolic "
                    "-Wl,--whole-archive (libip4tc.a and libip6tc.a); "
                    "--disable-nftables --disable-shared --enable-static",
        notes="Issue #43 supplies no version; 1.8.11 is chosen freely. "
              "The legacy IPv4 and IPv6 archives are linked whole into a "
              "corpus shared image, not an upstream-distributed binary. "
              "No CLI, extensions or nft dependencies are included; libc "
              "is dynamic. This is legitimate netfilter API code.",
    ),
}

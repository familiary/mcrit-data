"""BusyBox and toybox as Aboriginal Linux 1.4.4 ships them, harvested.

Issues #4 and #5 point at the Firmware Linux and Aboriginal Linux tarballs as
the source of the runtimes IoT malware links; the libgcc and libc families
take their archives. The same release also ships the userland every system
built with it runs: root-filesystem-<cpu>.tar.gz holds one statically linked
BusyBox and one statically linked toybox binary, with every command a
symlink to one of the two. Those binaries are harvested here, not rebuilt:

  * root-filesystem-i686.tar.gz, sha256
    e9e2d054ece79bdbf3eaed7dc25b1d010a0c5aafb06508e2023eafdaf25de5a5
  * root-filesystem-x86_64.tar.gz, sha256
    541c51684af6cef532ea67ca7d64c9a9a45ddb9ac9a524d2d0a2b89e89fbcafe

both from landley.net/aboriginal/downloads/old/binaries/1.4.4/root-filesystem/
as the Internet Archive holds them (snapshots 20170905111451 and
20170905111411; landley.net itself now only redirects there). Their
usr/src/MANIFEST says "Built on 2016-01-06" from BusyBox 1.24.1, toybox 0.6.1,
uClibc 0.9.33.2 and GCC 4.2.1, and the binaries print "BusyBox v1.24.1
(2016-01-06 ...)" and "toybox 0.6.1". Binary sha256: busybox i686
db3592941bd0761b6b43dc777095a1a04adfb47970e8c5b902150cd813e06560, x86_64
e11159a4994477e9f5f5d86fc2d58d0c287a397cdaea25d7ddaec84680fbf58a; toybox i686
1e49dc45453116a8c21ad6a4be9bf6be16f34bccd992c4b294a4d68d4e68dd14, x86_64
e7aa77b3e71b3c5f0c9241a68cf55bb46a74077025acd840819f7233408f71a3.

Both are stripped and static: no symbol survives, so min_named_ratio is 0,
and the statically linked uClibc and libgcc are in the image, unnamed, beside
the BusyBox or toybox code; a name-based glue filter has nothing to match, so
none is applied. They are therefore reference data for these exact shipped
binaries rather than for BusyBox or toybox source in general. The recorded
host toolchain only unpacked the archive; nothing is compiled.

The Firmware Linux 0.9.6 and Aboriginal 1.0.3 equivalents are not available:
the Internet Archive's CDX index holds only directory listings and 301
redirects for those releases' binaries/ directories, and no tarball.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_ARCHIVE = ("https://web.archive.org/web/%sid_/http://www.landley.net/"
            "aboriginal/downloads/old/binaries/1.4.4/root-filesystem/"
            "root-filesystem-%s.tar.gz")

_ROOTFS = {
    "x86": ("i686", "20170905111451",
            "e9e2d054ece79bdbf3eaed7dc25b1d010a0c5aafb06508e2023eafdaf25de5a5"),
    "x64": ("x86_64", "20170905111411",
            "541c51684af6cef532ea67ca7d64c9a9a45ddb9ac9a524d2d0a2b89e89fbcafe"),
}

_STAGE = Source(url="https://zlib.net/fossils/zlib-1.3.1.tar.gz",
                sha256="9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23")

RECIPES = {}
for _arch, (_cpu, _stamp, _digest) in _ROOTFS.items():
    for _family, _version, _upstream, _license in (
            ("busybox", "1.24.1-aboriginal1.4.4", "https://busybox.net/",
             "GPL-2.0-only"),
            ("toybox", "0.6.1-aboriginal1.4.4", "https://landley.net/toybox/",
             "0BSD")):
        RECIPES["%s_%s_%s" % (_family, _version, _arch)] = Recipe(
            family=_family, version=_version, upstream=_upstream,
            license=_license + " (statically linked uClibc 0.9.33.2: "
                    "LGPL-2.1-or-later)",
            source=_STAGE,
            extra_sources={"rootfs": Source(url=_ARCHIVE % (_stamp, _cpu),
                                            sha256=_digest)},
            build=[
                BuildStep("mkdir -p harvested && tar -xzf {rootfs} -C harvested "
                          "--strip-components=1 root-filesystem-%s/usr/bin/%s"
                          % (_cpu, _family)),
                BuildStep("cp harvested/usr/bin/%s %s.elf && sha256sum %s.elf"
                          % (_family, _family, _family)),
            ],
            artifacts=[Artifact(path="%s.elf" % _family,
                                component="%s.elf" % _family)],
            toolchains=["linux_" + _arch], requires=["tar"],
            drop_crt_glue=False, min_named_ratio=0,
            build_flags="Prebuilt by Aboriginal Linux 1.4.4 (GCC 4.2.1, "
                        "static uClibc 0.9.33.2, stripped); not compiled here",
            notes="Harvested from Aboriginal Linux 1.4.4 "
                  "root-filesystem-%s.tar.gz (sha256 %s, Internet Archive "
                  "snapshot %s of landley.net), usr/bin/%s, not rebuilt. "
                  "Static and stripped: no symbol survives and the "
                  "statically linked uClibc and libgcc are in the image "
                  "unnamed, so no glue filter applies and min_named_ratio is "
                  "0. The host toolchain only unpacked the archive. zlib is "
                  "only the staging directory." % (_cpu, _digest, _stamp,
                                                   _family),
        )

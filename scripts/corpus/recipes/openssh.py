"""OpenSSH portable - ssh, sshd, scp and sftp, built for Linux (ELF).

Targeted by backlog issue #46: ssh/sshd recompiled from patched OpenSSH source
in 21 SSHDoor families (ESET) and in Ebury (Operation Windigo). The reference
here is vanilla upstream: the families' modifications are the malware's, and
what this family lets an analyst do is subtract the legitimate OpenSSH code
from a trojanized binary. The sources (Botconf 2018, WeLiveSecurity) give no
OpenSSH version number, so versions were chosen by measurement, below. Nothing
is patched.

Which versions. Nine releases, x64, ssh + sshd (+ sshd-session and sshd-auth
where the release has them), PicHash overlap of the functions of 10 or more
instructions between the union of each release's binaries (percent of the row
release found in the column release):

          5.3   6.6   7.4   8.0   8.9   9.2   9.6  10.0  10.6
    5.3  100%    8%    3%    2%    0%    0%    0%    0%    0%
    6.6    7%  100%   32%   21%    1%    1%    1%    1%    0%
    7.4    2%   29%  100%   39%    1%    1%    1%    1%    1%
    8.0    1%   20%   39%  100%    2%    2%    2%    1%    1%
    8.9    0%    1%    1%    2%  100%   65%    3%    3%    2%
    9.2    0%    1%    1%    1%   63%  100%    5%    4%    2%
    9.6    0%    1%    1%    1%    3%    5%  100%   53%   31%
   10.0    0%    1%    1%    1%    2%    4%   51%  100%   35%
   10.6    0%    0%    1%    1%    2%    2%   28%   32%  100%

The releases fall in clusters: 5.3, 6.6, 7.4+7.6 (61%) and 8.0+8.4 (71%),
8.9+9.2 (65%), 9.6, and 10.x. The rows are the Linux distributions' OpenSSH
(RHEL 6 5.3, RHEL 7 7.4, RHEL 8 8.0, Ubuntu 22.04 8.9, Debian 12 9.2,
Ubuntu 24.04 9.6) plus 6.6, 10.0 and the latest 10.6p2. 7.6p1 (61% of 7.4p1),
8.4p1 (71% of 8.0p1) and 10.2p1 (54% of 10.0p1, 42% of 10.6p2) were measured
and not kept; 9.8p1 and 9.9p2 were not kept either (their sshd-session split is
in 10.0p1). On x86 the
overlap between two releases is 0-6% in every pair (see "The Linux half" in the
corpus README), so each release is separate reference data on that axis.

Which binaries. ssh and sshd are the issue's, and are built for every release.
10.0 and later split sshd: the sshd binary is the listener (1338 functions in
10.0p1), sshd-session (9.8 on) and sshd-auth (10.0 on) hold the
authentication and session code, so all of them are built. Of the rest, measured on 9.6p1 x64 by
functions of 10 or more instructions that ssh and sshd do not already have:
scp 82 of 328, sftp 77 of 323, ssh-keygen 68 of 638, ssh-agent 34 of 480,
ssh-keyscan 28 of 682, ssh-add 6, ssh-pkcs11-helper 2, sftp-server 1,
ssh-keysign 1. scp and sftp are the two client programs that add a code body
of their own (scp.c, sftp.c) and are built; the key tools are not the daemon
or the client, and add about 10% or less each. On 8.9 and later scp adds 82-85 beyond ssh and sshd and sftp
16-24 beyond those three; on 5.3-8.0 scp adds 24-25 and sftp 49-59.
ssh and sshd share 455-942 of their 10+ instruction PicHashes (they link the
same libssh.a and openbsd-compat), which is why they are separate artefacts
but not independent ones.

Link mode, and the vendored dependencies. OpenSSH's crypto is OpenSSL's
libcrypto, plus zlib and crypt(3). They are linked dynamically, as a
distribution's sshd is: NEEDED, not part of the image. So the image holds
OpenSSH's own code and its openbsd-compat replacements and nothing of
libcrypto, which data/OpenSSL (1.1.1w, 3.0.15, 3.5.8) already describes; a
static link would file OpenSSL's bodies under OpenSSH's name, the mistake the
corpus README records for -static builds. A statically linked sample matches
OpenSSL's family on libcrypto and this one on the rest. This was reasoned from
the corpus rules and from the NEEDED entries of the 7.4p1 x64 binaries (libcrypto, libz, libcrypt); a static OpenSSH
image was not built to measure. Each release is built against a private copy of the
library of its era, from a pinned tarball into a prefix per architecture (see
_elf_deps.py): OpenSSL 1.0.2u for 5.3p1, 6.6p1 and 7.4p1 (OpenSSL 1.1
support arrives in 7.6), 1.1.1w for 8.0p1 and 3.0.15 for 8.9p1 and later; zlib
1.3.1; libxcrypt 4.4.38, because glibc 2.39 has no crypt(3) and a 64-bit host
has no 32-bit libcrypt-dev (sshd's password check does not link for x86 without
it). The libraries are built the same way for both architectures so the two
halves are the same code. 32-bit libraries are not otherwise available here.

Not built: musl, since this host has no musl toolchain (no musl-gcc), so a
static-musl axis, which some malware ships, cannot be produced; MinGW and MSVC,
because OpenSSH portable does not build for Windows (the Win32-OpenSSH fork is
a different code base, recorded in the corpus README).

Sources. cdn.openbsd.org/pub/OpenBSD/OpenSSH/portable tarballs, each verified
against its detached .asc with the project's RELEASE_KEY.asc (the page
https://www.openssh.com/portable.html gives the fingerprint
7168B983815A5EEF59A4ADFD2A3F414E736060BA). Good signatures, but the signing
key of 5.3p1 is the 2001 DSA key 3981 992A 1523 ABA0 79DB FC66 CE8E CB03 86FF
9C48, revoked in 2013, and the keys of 6.6p1 to 8.4p1 have since expired; the
checks are against what the key file holds today. The pinned sha256 values are
of the verified tarballs.

Build. Upstream's configure, out of tree, then make of the named binaries:
--with-ssl-dir, --with-zlib and --with-ldflags pointing at the private
prefixes, and --without-zlib-version-check on every release (the checks in
these configure scripts reject zlib 1.3.1 as old). 5.3p1 and 6.6p1 need two
more things on a current toolchain, both as environment and not as patches:
CFLAGS -fcommon (GCC 10 stopped defaulting to it, and `subsystem_flag` is
defined in two objects) and the autoconf cache variable
ac_cv_func_arc4random=no (glibc 2.36 provides arc4random but those releases
call arc4random_stir, which the openbsd-compat replacement supplies only when
the function is absent). The other releases need neither. The hardening flags
upstream's configure picks for each release stay (stack protector,
_FORTIFY_SOURCE=2, PIE on the releases that enable it), with -O2 and
dynamic glibc. PAM, Kerberos, SELinux and libedit are off (configure defaults).

Measured on the artefacts (kept + removed = image), x64: ssh 1083 + 6 (5.3p1) to
2034 + 6 (10.6p2), sshd 1332 + 6 (5.3p1) to 2098 + 6 (9.2p1), 10.0p1 sshd 1338 +
6, sshd-session 2109 + 6, sshd-auth 2057 + 6; x86 the same counts to within a
few functions, with 6 to 10 removed. Of those 55-65% carry a symbol; the
rest are PLT stubs and anonymous pieces, above the 50% gate.

Glue that survives the baseline, by name and PicHash: on the x86 artefacts
_init (11 instructions), deregister_tm_clones (18), register_tm_clones (26),
__do_global_dtors_aux (21) and __stack_chk_fail_local (5), each with a
different PicHash per image (the GOT delta), the two-instruction
__x86.get_pc_thunk.bp/.cx/.si, and _start (16 instructions) in 30 of 40
artefacts. The x64 artefacts have none.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _elf_deps as deps


_MIRROR = "https://cdn.openbsd.org/pub/OpenBSD/OpenSSH/portable/openssh-%s.tar.gz"


def _openssh(version, sha256, openssl, binaries, cflags="", configure_env=""):
    """One OpenSSH release, built for both ELF architectures.

    ``cflags`` is appended to the toolchain's own (``-O2 -m32``/``-m64``).
    ``configure_env`` is shell ``NAME=value`` words placed before configure,
    for the autoconf cache variables a release needs on a modern glibc.
    """
    ssl = deps.prefix("openssl-%s" % openssl)
    zlib = deps.prefix("zlib-1.3.1")
    xcrypt = deps.prefix("libxcrypt-4.4.38")
    configure = (
        "mkdir -p build-{arch} && cd build-{arch} && "
        "LD_LIBRARY_PATH=%s/lib:%s/lib:%s/lib %s{source_root}/configure "
        "--with-ssl-dir=%s --with-zlib=%s --with-ldflags=-L%s/lib "
        "--without-zlib-version-check"
        % (ssl, zlib, xcrypt, configure_env, ssl, zlib, xcrypt))
    env = {"CFLAGS": "-O2 {archflag}" + (" " + cflags if cflags else "")}
    return Recipe(
        family="OpenSSH",
        version=version,
        upstream="https://www.openssh.com/portable.html",
        license="BSD-style, per file (see LICENCE in the tarball)",
        source=Source(url=_MIRROR % version, sha256=sha256),
        extra_sources={"zlib_src": deps.ZLIB, "xcrypt_src": deps.XCRYPT,
                       "openssl_src": deps.OPENSSL[openssl]},
        build=[BuildStep(deps.zlib_step()),
               BuildStep(deps.xcrypt_step()),
               BuildStep(deps.openssl_step(openssl)),
               BuildStep(configure, env=env),
               BuildStep("make -j$(nproc) " + " ".join(binaries), cwd="build-{arch}")],
        artifacts=[Artifact(path="build-{arch}/" + name, component=name)
                   for name in binaries],
        toolchains=["linux_x86", "linux_x64"],
        requires=["perl"],
        build_flags="-O2 plus the hardening flags upstream's configure selects "
                    "for the release (stack protector, _FORTIFY_SOURCE, PIE "
                    "where the release enables it)%s, dynamic OpenSSL %s, "
                    "zlib 1.3.1, libxcrypt 4.4.38 and glibc"
                    % (", -fcommon" if cflags else "", openssl),
        notes="Vanilla upstream, not the trojanized variants. OpenSSH's own "
              "code and openbsd-compat only: OpenSSL %s, zlib 1.3.1 and "
              "libxcrypt 4.4.38 are built from pinned tarballs and linked as "
              "shared libraries, so none of their code is in the image "
              "(see data/OpenSSL). Pinned by sha256 of a tarball whose GPG "
              "signature verified." % openssl,
    )


_CLIENTS = ["ssh", "sshd", "scp", "sftp"]
_SPLIT = ["ssh", "sshd", "sshd-session", "sshd-auth", "scp", "sftp"]

# -fcommon and the arc4random cache variable: see the module docstring.
_OLD = dict(cflags="-fcommon", configure_env="ac_cv_func_arc4random=no ")

RECIPES = {
    "OpenSSH_5.3p1": _openssh(
        "5.3p1", "d0c917462896974480b14454a8e1cb8b809291f67e5b9779c9b4dc4156c5ef12",
        "1.0.2u", _CLIENTS, **_OLD),
    "OpenSSH_6.6p1": _openssh(
        "6.6p1", "48c1f0664b4534875038004cc4f3555b8329c2a81c1df48db5c517800de203bb",
        "1.0.2u", _CLIENTS, **_OLD),
    "OpenSSH_7.4p1": _openssh(
        "7.4p1", "1b1fc4a14e2024293181924ed24872e6f2e06293f3e8926a376b8aec481f19d1",
        "1.0.2u", _CLIENTS),
    "OpenSSH_8.0p1": _openssh(
        "8.0p1", "bd943879e69498e8031eb6b7f44d08cdc37d59a7ab689aa0b437320c3481fd68",
        "1.1.1w", _CLIENTS),
    "OpenSSH_8.9p1": _openssh(
        "8.9p1", "fd497654b7ab1686dac672fb83dfb4ba4096e8b5ffcdaccd262380ae58bec5e7",
        "3.0.15", _CLIENTS),
    "OpenSSH_9.2p1": _openssh(
        "9.2p1", "3f66dbf1655fb45f50e1c56da62ab01218c228807b21338d634ebcdf9d71cf46",
        "3.0.15", _CLIENTS),
    "OpenSSH_9.6p1": _openssh(
        "9.6p1", "910211c07255a8c5ad654391b40ee59800710dd8119dd5362de09385aa7a777c",
        "3.0.15", _CLIENTS),
    "OpenSSH_10.0p1": _openssh(
        "10.0p1", "021a2e709a0edf4250b1256bd5a9e500411a90dddabea830ed59cef90eb9d85c",
        "3.0.15", _SPLIT),
    "OpenSSH_10.6p2": _openssh(
        "10.6p2", "9ae44872090cf2f06b3cf9ff147e7f16f309671340763ed2f99248398ae29d5b",
        "3.0.15", _SPLIT),
}

"""Tiny SHell (mcrit-data issue #52) - the tsh/tshd pair, ELF x86/x64.

Christophe Devine's minimal encrypted backdoor: a server (`tshd`) that
accepts a connection, authenticates it through a hand-rolled Packet
Encryption Layer, and offers file upload, file download and a shell, and a
client (`tsh`) that drives it. Mandiant's March 2025 reporting on UNC3886
describes six TINYSHELL-derived backdoors on Junos routers - `appid`, `to`,
`irad`, `lmpad`, `jdosd`, `oemd` - and links this repository directly; its
hunting rule keys on six upstream function names, `tsh_get_file`,
`tsh_put_file`, `tsh_runshell` and the three `tshd_` equivalents, all of
which are in the artefacts here.

Two binaries come out of one source tree, so this is one family with two
components. `tshd` is the one that matters: it is the implanted half.

**These are dynamically linked PIE executables, not `-static`.** That is
worth stating because it is what makes an ELF *executable* safe to put in
this corpus at all. `scripts/corpus/README.md` argues for building a `.so`
rather than an executable, and the reason is attribution: a `-static` link
would pull all of glibc into the image under this family's name, which is
what happened to monomorph (1393 of its 1397 symbols were glibc and zlib).
Upstream links neither statically nor with `-s`, so glibc stays in
`libc.so.6` and every function in these images is the project's own or a
`.plt` stub.

**Three things in the issue's build analysis did not survive contact with
the tree, and are corrected here.**

*The self-test mains are already guarded.* Issue #52 records that `aes.c`
and `sha1.c` each contain their own `main()` and warns they must not reach
the link. They do contain one - `aes.c:616` and `sha1.c:282` - but both sit
inside `#ifdef TEST` (`aes.c:585`, `sha1.c:259`), so they are compiled out
unless `TEST` is defined and nothing has to be done about them. Linking all
four translation units together produces no duplicate `main`.

*`-O3` is reachable, and is what is used.* The issue reads the `linux:`
target, which hardcodes `gcc -O -W -Wall` and so ignores the `CFLAGS = -O3
-W -Wall` on `Makefile:4`, and concludes that the real Linux build is `-O`.
That is true of the `linux:` target. But `linux_x64:` does not compile
anything itself - it re-enters make with `DEFS=-DLINUX` and lets the generic
`$(TSH)`/`$(TSHD)` rules at `Makefile:120-126` do the work, and those honour
`$(CFLAGS)`. So upstream has both levels on the Linux path, and this recipe
uses the `-O3` one, which is the value `Makefile:4` declares. The level is
recorded in `build_flags` either way, because an `-O` reference will not
match an `-O3` sample well.

*The strip is overridable; no hand-rolled link is needed.* Both the `linux:`
target and the generic rules end by stripping, which would make these
reports mostly anonymous and so a build failure here. But `Makefile:3` is
`STRIP = strip` and the rules invoke `$(STRIP)`, so `STRIP=true` neutralises
it from the command line - the exact override `scripts/corpus/README.md`
names for GCC build systems. Upstream's own rules therefore do the compile
and the link; nothing is replicated by hand and no source is touched. The
generic rules are invoked directly rather than through `linux_x64:` only so
that `{archflag}` can reach `CFLAGS` and `LDFLAGS` for the 32-bit axis;
`DEFS=-DLINUX` and the `-Xlinker --no-as-needed -lutil` link line are copied
from `linux_x64:` unchanged.

**Measured.** Symbol-carrying functions in the built images:

    tsh    x86  44      tshd  x86  34
    tsh    x64  33      tshd  x64  29

20 of `tshd`'s are the project's own (`tshd_*`, `pel_*`, `aes_*`, `sha1_*`)
on both architectures. The issue worries that only 4 to 6 functions per
image are "real" project code - `tsh.c` and `tshd.c` define six apiece,
two of which are `main` and `usage` - and asks whether `min_functions`
needs lowering the way 4g3nt47/Obfuscator needed it. It does not: the
corpus counts what is in the image, and `pel.c`'s seven functions and the
`aes.c`/`sha1.c` primitives are upstream code that genuinely ships inside
every tsh binary. Every artefact here clears the floor of eight several
times over, so that knob is left alone.

**`min_named_ratio` is lowered, and the unnamed functions are accounted for
exactly.** The symbol gate measures named functions over functions of three
instructions or more, and on x64 these score below its default:

    x86   tshd 118 functions reported   tsh 122      (gate passes)
    x64   tshd  27 of 68 named (40%)    tsh 30 of 72 (42%)

Nothing is stripped - `STRIP=true` saw to that, and every one of the
project's own functions carries its name. What dilutes the ratio is the
`.plt`, and the arithmetic closes with no remainder: `tshd` x64 has 41
`.rela.plt` relocations (0x3d8 bytes at 24 bytes per `Elf64_Rela`) and SMDA
reports 68 - 27 = **41** unnamed functions; `tsh` x64 has 42 and SMDA
reports 72 - 30 = **42**. Every unnamed function in these images is a
libc import stub, against 46 and 47 undefined dynamic symbols respectively.
They cannot be filtered out the way the PE side's import thunks are, because
an ELF `.plt` entry carries no symbol for `baseline.py` to match on, and
they are three instructions long on x86-64 while i386's fall below the
gate's cut - the same ABI difference the Azazel recipe records.

So `min_named_ratio=0.38` is set, below the 0.397 that `tshd` x64 measures.
This is a small program that calls libc a lot, which is what a 1990s
backdoor is; the ratio is a property of that shape rather than of a defect,
and the x86 artefacts are the control.

**The aes/sha1 overlap with mbedTLS is real and is the thing to watch.**
`aes.c` and `sha1.c` are Devine's own implementations, the direct ancestors
of XySSL, then PolarSSL, then mbedTLS - which is four versions and 26
artefacts in this corpus. They are not duplicates of each other, 20-odd
years apart, but they are the same author's same algorithms, so this is the
`data/libsodium` ed25519-ref10 situation rather than a clean separation.
The cross-family PicHash census is where that shows up and is reported with
this family rather than assumed away.

**The samples are FreeBSD/Junos; these artefacts are Linux.** Mandiant's
six backdoors run on Junos routers, so a Linux ELF build is a toolchain
proxy for them and not a container match. It is still the right first axis -
the project code is identical and the function names the hunting rule keys
on are the same - but a byte-level comparison against a Junos sample should
not be expected to line up, and `notes` says so.

**Licence.** Every source file header carries "this program is licensed
under the GPL"; there is no `LICENSE` or `COPYING` file anywhere in the
tree, and no version of the GPL is named. Recorded as the fact it is.
Upstream also disagrees with itself about the version: `Makefile:13` is
`VERSION=tsh-0.7` while `tsh.c:2` still says "Tiny SHell version 0.6".
0.7 is used, being the build system's own number.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Upstream's own $(TSH)/$(TSHD) rules (Makefile:120-126), with the flags
# linux_x64: passes them, plus {archflag} so one line serves both ABIs and
# STRIP=true so the rules' trailing $(STRIP) does nothing. Nothing here is a
# replacement for an upstream command; it is upstream's command line.
_BUILD = ('make tsh tshd CC={cc} CFLAGS="-O3 -W -Wall {archflag}" '
          'DEFS="-DLINUX" '
          'LDFLAGS="{archflag} -Xlinker --no-as-needed -lutil" '
          'STRIP=true')


RECIPES = {
    "TinySHell_0.7": Recipe(
        family="TinySHell",
        version="0.7",
        upstream="https://github.com/creaktive/tsh",
        license="GPL, stated in each source file header ('this program is "
                "licensed under the GPL'); no LICENSE or COPYING file in the "
                "tree and no GPL version named",
        source=Source(git_url="https://github.com/creaktive/tsh.git",
                      git_ref="5ec48d4193a726e41d129e4d01ecf56f07919be0"),
        build=[BuildStep(_BUILD)],
        artifacts=[
            # is_library stays true, as it is for every executable in this
            # corpus. The flag is not "this file is a shared library": MCRIT
            # keys its library-only views and its library-versus-malware
            # family counts off it, so a false here would file reference
            # material as malware. validate() checks it for that reason.
            Artifact(path="tshd", component="tshd"),
            Artifact(path="tsh", component="tsh"),
        ],
        toolchains=["linux_x86", "linux_x64"],
        # tshd x64 measures 0.397 over functions of three instructions or
        # more. Nothing is stripped and every project function is named; the
        # shortfall is the .plt, exactly 41 unnamed functions against 41
        # .rela.plt relocations in tshd and 42 against 42 in tsh. An ELF
        # import stub carries no symbol, so baseline.py cannot match it the
        # way it matches a PE import thunk. See the docstring.
        min_named_ratio=0.38,
        build_flags="make tsh tshd through upstream's own $(TSH)/$(TSHD) "
                    "rules with CFLAGS=\"-O3 -W -Wall\" (the level "
                    "Makefile:4 declares; the linux: target's hardcoded -O "
                    "is the other one upstream offers), DEFS=-DLINUX and "
                    "LDFLAGS=\"-Xlinker --no-as-needed -lutil\" copied from "
                    "the linux_x64: target, plus -m32/-m64; STRIP=true "
                    "neutralises the $(STRIP) on Makefile:122 and :126. "
                    "Dynamically linked PIE, not -static and not -s",
        notes="Christophe Devine's minimal encrypted backdoor, built as the "
              "two binaries one tree produces: tshd (the implanted server, "
              "the component that matters) and tsh (the client). Mandiant's "
              "March 2025 UNC3886 reporting links this repository for six "
              "TINYSHELL-derived Junos backdoors (appid, to, irad, lmpad, "
              "jdosd, oemd) and keys its hunting rule on tsh_get_file, "
              "tsh_put_file, tsh_runshell, tshd_get_file, tshd_put_file and "
              "tshd_runshell, all present here. Those samples are "
              "FreeBSD/Junos, so these Linux ELF artefacts are a toolchain "
              "proxy for them rather than a container match. Symbol-carrying "
              "functions: tsh 44 / tshd 34 on x86, tsh 33 / tshd 29 on x64, "
              "of which 20 in tshd are the project's own on both. Linked "
              "dynamically, so glibc is not in the image under this family's "
              "name - the trap -static set for monomorph. aes.c and sha1.c "
              "are Devine's own implementations and the direct ancestors of "
              "XySSL, PolarSSL and mbedTLS, which is four versions and 26 "
              "artefacts here: not duplicates twenty years apart, but the "
              "same author's same algorithms, so read the cross-family "
              "PicHash census for this family with that in mind, as with "
              "libsodium's ed25519-ref10. The aes.c and sha1.c self-test "
              "main() functions sit inside #ifdef TEST (aes.c:585, "
              "sha1.c:259) and are compiled out, so linking all four "
              "translation units raises no duplicate main - correcting the "
              "concern recorded in issue #52. Upstream disagrees with itself "
              "on the version: Makefile:13 says tsh-0.7, tsh.c:2 says 0.6.",
    ),
}

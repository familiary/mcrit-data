"""f0rb1dd3n/Reptile (mcrit-data issue #54) - the userland half, ELF x86/x64.

Reptile is an LKM rootkit with a userland toolkit beside it. Mandiant's
reporting puts it on UNC3886's FortiManager intrusions. Two halves, and only
one of them is here:

* `kernel/` is **not built**. It is a `.ko`, and `scripts/corpus/README.md`
  records in full why a relocatable kernel object cannot be turned into
  correct reference data by this pipeline: no program headers, every section
  at address 0, so SMDA has no layout and either finds nothing or attaches
  names to the wrong bodies. That is an SMDA limitation, not a property of
  this project, and it holds whatever is decided about kernel versions.
* `userland/` is this recipe. Four binaries: `shell` and `cmd`, which
  upstream's own Makefile comments describe as the ones that "stay in the
  victim machine", and `listener` and `packet`, which stay on the attacker's.
  All four are ordinary dynamically linked PIE executables, so none of the
  `.ko` problem touches them.

**Two build values are pinned here, and that is a deliberate departure from
upstream's build path - the only one in this recipe.** `scripts/random.sh`
derives `AUTH` and `HTUA` from `/dev/urandom` and appends them to `.config`,
and the `%config` target runs it, so even `make defconfig` randomises them.
`userland/Makefile` then compiles `shell` and `cmd` with
`-DAUTH=$(AUTH) -DHTUA=$(HTUA)`, which puts both values into the code as
32-bit immediates. Upstream's build is therefore not reproducible by
construction: two builds of one commit differ, and a recorded `sha256` would
describe nothing.

So this recipe pins them, to `AUTH=0x52657074` and `HTUA=0x696c6521`. Both
are visibly synthetic (ASCII `Rept` and `ile!`) so that nobody mistakes them
for values observed in a sample, and they are written into `build_flags` so
this artefact can be reproduced exactly. The cost is bounded and worth
stating precisely: the handful of functions that compare against those
immediates will not match the corresponding function in a real sample, which
carries that actor's random pair. Every other function is unaffected. The
alternative - letting `/dev/urandom` decide - produces reference data whose
digest means nothing, which is worse.

Everything else is upstream's. The remaining configuration comes from
`configs/defconfig` unchanged, which is upstream's shipped default:
`HIDE="reptile"` (passed as `-DNAME`), and `MAGIC_VALUE="hax0r"`,
`PASSWORD="s3cr3t"`, `SRCPORT=666` and `TAG_NAME="reptile"`, which the
userland binaries do not read. No `.config` is generated, because passing
the three defines directly is the same thing without the random step.

**The compile lines are issued directly rather than through `make`**, for one
reason: `userland/Makefile` ends each rule with a literal `strip`, not
`$(STRIP)`, so there is no variable to override the way Tiny SHell's
`STRIP=true` does. The lines below are that Makefile's own, flag for flag,
minus the strip - including the pipe through upstream's
`scripts/destringify.pl`, which is its own source transformation and is kept.

**The vendored Tiny SHell code is the thing to watch.**
`userland/crypto/aes.c`, `userland/crypto/sha1.c` and
`userland/transport/pel.c` are Christophe Devine's - `pel.c`'s header reads
"Packet Encryption Layer for Tiny SHell" and upstream's README credits
creaktive/tsh. They are in `DEP_SRC`, so they are linked into `shell` and
`listener` but not into `cmd` or `packet`. The `TinySHell` family in this
corpus is built from that same upstream, so those bodies are in both
families' artefacts by construction. This is the `data/Hidden`/Zydis
situation: the overlap is real code sharing rather than misattribution, and
it is measured and recorded rather than filtered, because subtracting it
would mean claiming Reptile does not contain the code it demonstrably ships.
Read this family's cross-family PicHash census with that in mind.

**Measured.** Symbol-carrying functions in the built binaries:

    shell     x86 32    x64 27
    cmd       x86 11    x64  8
    listener  x86 56    x64 45
    packet    x86 29    x64 17

`cmd` x64 sits exactly on the eight-function floor. That is the project's
own count rather than a build accident - it is a small command shim - and
`min_functions` is left alone because the floor is met.

**Licence: none.** The repository ships `DISCLAIMER.md` and no `LICENSE`
file. Recorded as the fact it is, which is this corpus's rule.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# The two pinned values, spelled once. See the docstring: upstream randomises
# these per build, which is what makes its own build path unusable here.
_AUTH = "0x52657074"
_HTUA = "0x696c6521"

# userland/Makefile's CFLAGS, INCLUDES and the EXTRA_FLAGS its userland_bin
# target passes, plus {archflag}. -O3 -fPIC is upstream's.
_C = ("-Iinclude -O3 -fPIC -D_REPTILE_ -DAUTH=%s -DHTUA=%s" % (_AUTH, _HTUA))

# upstream's DEP_SRC: the vendored Tiny SHell translation units.
_DEP = "crypto/aes.c crypto/sha1.c transport/pel.c"

_MKDIR = "mkdir -p out"

# Each of upstream's four rules, verbatim apart from {archflag} and the
# trailing `strip` that is not run. HIDE="reptile" comes from
# configs/defconfig and reaches shell as -DNAME.
_SHELL = ('cat shell.c | perl ../scripts/destringify.pl | '
          '{cc} {archflag} %s -DNAME=\\"reptile\\" %s -o out/shell -xc - -lutil'
          % (_C, _DEP))
_CMD = ('cat cmd.c | perl ../scripts/destringify.pl | '
        '{cc} {archflag} %s -o out/cmd -xc -' % _C)
_LISTENER = ('{cc} {archflag} %s %s client/listener.c -o out/listener -lreadline'
             % (_C, _DEP))
_PACKET = '{cc} {archflag} %s client/packet.c -o out/packet' % _C


RECIPES = {
    "Reptile_2026-08-17": Recipe(
        family="Reptile",
        version="2026-08-17",
        upstream="https://github.com/f0rb1dd3n/Reptile",
        license="none stated: the tree ships DISCLAIMER.md and no LICENSE "
                "file. The vendored userland/crypto/aes.c, "
                "userland/crypto/sha1.c and userland/transport/pel.c are "
                "Christophe Devine's, credited by upstream's README to "
                "creaktive/tsh, and are GPL by their own file headers",
        source=Source(git_url="https://github.com/f0rb1dd3n/Reptile.git",
                      git_ref="30651814619cb56d67ca6681cb937278b15b11ea"),
        build=[BuildStep(_MKDIR, cwd="userland"),
               BuildStep(_SHELL, cwd="userland"),
               BuildStep(_CMD, cwd="userland"),
               BuildStep(_LISTENER, cwd="userland"),
               BuildStep(_PACKET, cwd="userland")],
        artifacts=[
            Artifact(path="userland/out/shell", component="shell"),
            Artifact(path="userland/out/cmd", component="cmd"),
            Artifact(path="userland/out/listener", component="listener"),
            Artifact(path="userland/out/packet", component="packet"),
        ],
        toolchains=["linux_x86", "linux_x64"],
        # Same measurement as TinySHell and for the same cause: these are
        # small dynamically linked executables that call libc a lot, and an
        # ELF .plt entry carries no symbol for baseline.py to match the way a
        # PE import thunk does. Nothing is stripped - the literal `strip` in
        # upstream's rules is the reason the compile lines are issued
        # directly - and every one of the projects' own functions is named.
        min_named_ratio=0.3,
        build_flags="upstream's userland/Makefile compile lines, flag for "
                    "flag: gcc -Iinclude -O3 -fPIC -D_REPTILE_ with "
                    "shell.c and cmd.c piped through "
                    "scripts/destringify.pl, DEP_SRC "
                    "(crypto/aes.c crypto/sha1.c transport/pel.c) linked "
                    "into shell and listener, -lutil on shell and "
                    "-lreadline on listener, plus -m32/-m64; the literal "
                    "`strip` ending each rule is not run. AUTH and HTUA are "
                    "PINNED to 0x52657074 and 0x696c6521 because "
                    "scripts/random.sh derives them from /dev/urandom and "
                    "they are compiled in as immediates, so upstream's own "
                    "build is not reproducible; -DNAME=\"reptile\" is "
                    "configs/defconfig's HIDE value unchanged",
        notes="The userland half only. kernel/ is a .ko and is not built: a "
              "relocatable kernel object has no program headers and every "
              "section at address 0, so SMDA has no layout to work from and "
              "either finds nothing or attaches names to the wrong bodies - "
              "see the not-built table, where this is recorded in full. The "
              "four binaries here are ordinary dynamically linked PIE "
              "executables; upstream's Makefile comments describe shell and "
              "cmd as the pair that stays on the victim machine and "
              "listener and packet as the attacker's. Counts: shell 32/27, "
              "cmd 11/8, listener 56/45, packet 29/17 symbol-carrying "
              "functions on x86/x64, with cmd x64 exactly on the "
              "eight-function floor, which is the project's own size. AUTH "
              "and HTUA are pinned rather than taken from /dev/urandom, the "
              "only departure from upstream's build path: both are visibly "
              "synthetic (ASCII Rept and ile!) so they are not mistaken for "
              "observed values, and the functions comparing against them "
              "will not match a real sample's, which carries that actor's "
              "random pair. Everything else is upstream's, with the rest of "
              "the configuration taken unchanged from configs/defconfig. "
              "userland/crypto/aes.c, userland/crypto/sha1.c and "
              "userland/transport/pel.c are Christophe Devine's Tiny SHell "
              "code, credited as such by upstream's README, and are in "
              "DEP_SRC so they are linked into shell and listener but not "
              "cmd or packet; the TinySHell family here is built from that "
              "same upstream, so those bodies are genuinely in both "
              "families - real code sharing rather than misattribution, "
              "measured and recorded rather than filtered, as with "
              "data/Hidden and Zydis.",
    ),
}

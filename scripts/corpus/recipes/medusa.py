"""ldpreload/Medusa (mcrit-data issue #40) - LD_PRELOAD hook set, ELF x86/x64.

A ring-3 rootkit of the same shape as Azazel: a shared object installed
through `/etc/ld.so.preload` so the dynamic linker interposes its versions of
the libc, PAM, utmp and libpcap entry points ahead of the real ones. Intezer's
reporting describes OrBit as a rebuild of this project.

Only `build/rkld.so` is built. Upstream's `all:` target does three further
things, and each is left out for its own reason, documented below. Nothing
built here is run except the build-time string generator, which is what the
first section is about.

**The build runs upstream's configuration generator, and that was a
maintainer decision rather than a default.** `src/rkld.c:33` and
`src/rknet.c:19` both `#include "../build/xor.h"`, which is not in the tree.
It is produced by compiling `src/config.c` and *running* it: `config.c:351`
opens `./build/xor.h` for writing and `xor_dump()` fills it with XOR-obfuscated
copies of the constants hardcoded at the top of that same file. So unlike
Azazel - where the equivalent header is committed upstream, and was verified
to be the generator's default output without running anything - this project
has no path to a compiled `.so` that does not execute a build-time binary
first.

What that binary does was read before it was run, and is narrow: its only
side effects are `unlink("./build/xor.h")`, `open` of the same path, and
`write` calls into it. It opens no socket, execs nothing, and writes nothing
outside `build/`. Its output is upstream's own defaults, not operator input -
there is no configuration to supply. On that basis it is the same category as
LuaJIT's host-built `buildvm`, which this corpus already runs mid-build and
which `toolchain.placeholders`' `{hostcc}` exists for. It is still worth
naming in a docstring, because "the recipe runs a binary it just compiled from
the fetched tree" is not something a reader should have to discover from the
build steps.

**What upstream's `all:` target does that this recipe does not.**

* It **modifies the host it builds on**, with
  `sudo sed -i 's/^#PermitRootLogin prohibit-password/PermitRootLogin yes/'
  /etc/ssh/sshd_config` followed by `sudo systemctl restart sshd`. That is in
  the default target rather than an `install:` one, which is why `make` is
  never invoked here and the compiler lines are issued directly. Those two
  lines are the whole reason this recipe does not simply call `make`.
* It builds `bin/rkload`, the loader, which is **not** collected. It links
  `-static`, so all of glibc would enter under this family's name - the trap
  that keeps monomorph out of this corpus - and it embeds the finished `.so`
  as a C array through `xxd -i build/rkld.so > build/rkld.h`, so the artefact
  would additionally carry the implant as data. Either reason alone is enough.
* It generates `include/arch.h` from `uname -m`. This recipe generates the
  same file with upstream's own three `echo` lines, keyed on the target
  rather than the host, because that header decides which half of the source
  compiles. `src/rkld.c:1653` guards one `sys_connect`/`sys_bind` pair with
  `#ifdef __i386__` and `:1664` guards a second with `#ifdef __AMD64__`; gcc
  defines `__i386__` itself under `-m32`, so an x86 build against the host's
  x64 `arch.h` compiles **both** and fails with
  `redefinition of 'sys_connect'`. Keying the header on `{bitness}` is what
  upstream's Makefile would emit on an i686 host.

**`-fvisibility=hidden` is not passed, for the reason the Azazel recipe
argues at length**: this is an interposition library, so its exported names
*are* the artefact, and hiding `open`, `__xstat` or `pam_authenticate` would
produce something `ld.so.preload` cannot use. Issue #40 recommends the flag;
that recommendation is right for a normal ELF library and wrong here. The
cost is the same unnamed `.plt` residue, and it is measured below rather than
hidden.

**No optimization.** There is no `-O` anywhere in upstream's `Makefile`, so
this builds at `-O0`. Issue #40 records `-O2` as the default; that is not
what the file says, and the level is recorded in `build_flags` as built.

**Measured.** 80 symbol-carrying functions on x64 and 84 on x86. The hook set
is visible in the dynamic symbol table and spans libc (`open`, `stat`,
`execve`, `unlink`, `readdir`, `read`, `write`, `chmod`, `chown`,
`truncate`), PAM (`pam_authenticate`, `pam_open_session`, `pam_acct_mgmt`,
`pam_sm_authenticate`), utmp (`pututline`, `updwtmp`), libpcap (`pcap_loop`)
and TCP wrappers (`hosts_access`), plus this project's own helpers
(`patch_ld`, `rename_ldpath`, `clean_ports`, `get_mod_list`, `pathmatch`,
`unconfined_exec`, `xread`).

**The 21-name overlap with Azazel is now measurable, which is the point of
building this.** Issue #55 asks that the two be decided together and lists 21
symbol names they share - `__lxstat`, `__lxstat64`, `__xstat`, `__xstat64`,
`access`, `execve`, `fopen`, `getpwnam_r`, `lstat`, `lstat64`, `open`,
`opendir`, `pam_acct_mgmt`, `pam_authenticate`, `pam_open_session`,
`pam_sm_authenticate`, `pcap_loop`, `stat`, `stat64`, `unlink`, `unlinkat` -
and the Azazel recipe had to record that overlap as unmeasurable because this
family did not exist. It does now, and the cross-family PicHash census is
where a shared *body* would show up. Sharing a name is expected and means
nothing on its own: both projects hook the same libc, so both necessarily
define functions called `open`. What would matter is two identical bodies,
which is what `validate --deep` reports on.

`src/rknet.c` **is** part of the default build - upstream's line is
`$(CC) src/rkld.c src/rknet.c -o build/rkld.so` - correcting issue #40, which
records it as excluded. Both translation units are therefore in this artefact.

**Dependencies.** `tcpd.h` from libwrap for `hosts_access`, plus libpcap's
headers and `-ldl`. Upstream links only `-ldl`, so like Azazel the artefact
carries undefined references to the rest; a shared object is permitted to.

**Licence: none.** There is no `LICENSE` file and no licence header in any
source file. Recorded as the fact it is, which is this corpus's rule, not a
judgement about the project.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_DIRS = "mkdir -p build bin"

# Upstream's own arch.h generation, keyed on the target rather than the host's
# uname -m. See the docstring: this header picks which sys_connect/sys_bind
# pair compiles, and getting it wrong is a hard error rather than a wrong
# shape.
_ARCH_H = ('{ echo "#ifndef __ARCH_H"; echo "#define __ARCH_H"; '
           'echo "#define WORDSIZE {bitness}"; '
           'echo "#define $([ {bitness} = 32 ] && echo __i386__ || echo __AMD64__) 1"; '
           'echo "#endif"; } > include/arch.h')

# The generator is a host tool: it runs on the build machine and only writes a
# text header, so it is compiled without {archflag} on both axes.
_GEN = "{cc} src/config.c -o build/config"
_RUN_GEN = "./build/config"

# Upstream's compile line for the shared object, verbatim apart from
# {archflag}. The `strip` upstream applies to the loader is not reached
# because the loader is not built.
_SO = ("{cc} {archflag} src/rkld.c src/rknet.c -o build/rkld.so "
       "-fPIC -shared -ldl -D_GNU_SOURCE")


RECIPES = {
    "Medusa_2025-04-05": Recipe(
        family="Medusa",
        version="2025-04-05",
        upstream="https://github.com/ldpreload/Medusa",
        license="none stated: no LICENSE file in the tree and no licence "
                "header in any source file",
        source=Source(git_url="https://github.com/ldpreload/Medusa.git",
                      git_ref="fdade060f4bc53a356fe62c14e9c830fcc0b968e"),
        build=[BuildStep(_DIRS), BuildStep(_ARCH_H), BuildStep(_GEN),
               BuildStep(_RUN_GEN), BuildStep(_SO)],
        artifacts=[Artifact(path="build/rkld.so", component="rkld.so")],
        toolchains=["linux_x86", "linux_x64"],
        # Measured, not guessed. The symbol gate takes its ratio over
        # functions of three instructions or more and BEFORE runtime glue is
        # dropped, so this is the number the gate itself reports: x64 scores
        # 71 of 146 = 0.486, x86 passes the 0.5 default outright. 0.48 sits
        # just under the x64 figure so that a future build which loses more
        # symbol coverage still fails. Nothing is stripped and every one of
        # this project's functions carries its name; what dilutes the ratio
        # is the unnamed .plt residue that comes of keeping the hooks
        # exported, which an interposition library has to do.
        min_named_ratio=0.48,
        build_flags="gcc -O0 (upstream's Makefile sets no -O at all) -fPIC "
                    "-shared -ldl -D_GNU_SOURCE over src/rkld.c and "
                    "src/rknet.c, which is upstream's own compile line; "
                    "include/arch.h generated with upstream's echo lines but "
                    "keyed on the target bitness rather than the host's "
                    "uname -m; build/config compiled and run to emit "
                    "build/xor.h, which rkld.c and rknet.c include; "
                    "upstream's sudo sshd_config edit, its xxd step and its "
                    "-static bin/rkload loader are deliberately not run",
        notes="A ring-3 LD_PRELOAD rootkit, the shape Intezer describes OrBit "
              "as a rebuild of. Only build/rkld.so is collected. Upstream's "
              "all: target is not invoked at all, because it modifies the "
              "host it builds on: it runs sudo sed -i on "
              "/etc/ssh/sshd_config to set PermitRootLogin yes and then "
              "restarts sshd, in the default target rather than an install: "
              "one. The compiler lines are therefore issued directly. Two "
              "further parts of that target are left out on their own "
              "merits: bin/rkload links -static, which would put all of "
              "glibc under this family's name as it did for monomorph, and "
              "it embeds the finished .so as a C array via xxd -i, so it "
              "would carry the implant as data. The build does compile and "
              "run upstream's src/config.c, because rkld.c:33 and "
              "rknet.c:19 include ../build/xor.h which only that binary "
              "produces; it was read before being run and its only side "
              "effects are unlink, open and write on ./build/xor.h, filling "
              "it with XOR-obfuscated copies of constants hardcoded in "
              "config.c itself - upstream's defaults, with no operator "
              "input, which is the same category as LuaJIT's host-built "
              "buildvm. 80 symbol-carrying functions on x64 and 84 on x86. "
              "Built WITHOUT -fvisibility=hidden, as Azazel is and for the "
              "same reason: an interposition library's exports are the "
              "artefact. include/arch.h is generated per target rather than "
              "per host because rkld.c:1653 and :1664 guard two "
              "sys_connect/sys_bind pairs with __i386__ and __AMD64__, and "
              "gcc defines __i386__ itself under -m32, so an x86 build "
              "against an x64 arch.h fails with redefinition of "
              "'sys_connect'. src/rknet.c IS in upstream's default build "
              "line, correcting issue #40. There is no -O anywhere in the "
              "Makefile, so this is -O0, also correcting that issue. Needs "
              "libwrap (tcpd.h) and libpcap headers. Issue #55 lists 21 "
              "symbol names shared with Azazel; that overlap is measurable "
              "now that both families exist, and sharing a name is expected "
              "since both hook the same libc - a shared PicHash would be the "
              "finding, and the deep check is what reports it.",
    ),
}

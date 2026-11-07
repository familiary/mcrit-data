"""MIRACL (Shamus Software / CertiVox big-number and ECC library), ELF builds.

Requested because LockBit 3.0's keygen is reported to be built on MIRACL;
the evidence for that is naming only. **The variant that matches that keygen
is unknown** (see _miracl.UNKNOWN), so the library is built in every
configuration upstream ships a ready template for, as separate versions, and
the family records them as such rather than guessing.

Nothing upstream is edited. mirdef.h is not in the source tree under that
name as a file that can be changed in place: include/mirdef.h is a tracked
copy of the 32-bit template, and the build copies include/ into a build
directory, overwrites mirdef.h there with upstream's own template for the
variant, and compiles with -I on that directory. The only additions are
command-line defines.

Variants (ELF):
  generic32  include/mirdef.h32 + -DMR_NOASM, -m32. h32 spells its 64-bit
             type __int64; GCC has none, so -D__int64='long long'. That is the
             only difference between h32 and upstream's mirdef.lnx
             (diffed: comments and that spelling), so h32 is used and the
             spelling supplied on the command line. MR_NOASM selects the C
             muldiv in mrcore.c, so mrmuldv.c is not compiled.
  generic64  include/mirdef.h64 + -DMR_NOASM, -m64. h64 defines no
             double-width type and MR_NOASM needs one, so
             -Dmr_dltype=__int128.
  asm32      include/mirdef.lnx + source/mrmuldv.gcc as mrmuldv.c: upstream's
             lib/linux script, -m32.
  asm64      include/mirdef.h64 + source/mrmuldv.g64 as mrmuldv.c: upstream's
             lib/linux64 script, -m64.
The module list is lib/linux64's: 50 C modules and the C++ wrappers big, zzn,
ecn, ec2, crt and flash. The example programs and source/curve/ are not
built. -O2 as in the scripts, plus -fPIC and a -shared link so there is an
image SMDA can read; every symbol stays exported and the object is not
stripped.

Measured results: see the table in the README and the overlap block below.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _miracl as m

_SPEC = {
    # variant: (toolchain, template, extra defines, mrmuldv source, archflag)
    "generic32": ("linux_x86", "mirdef.h32",
                  "-DMR_NOASM -D'__int64=long long'", None),
    "generic64": ("linux_x64", "mirdef.h64",
                  "-DMR_NOASM -Dmr_dltype=__int128", None),
    "asm32": ("linux_x86", "mirdef.lnx", "", "mrmuldv.gcc"),
    "asm64": ("linux_x64", "mirdef.h64", "", "mrmuldv.g64"),
}


def _compile(driver, defines, mods, ext):
    return ("for f in %s; do %s {archflag} -O2 -fPIC %s -I. -c ../source/$f.%s"
            " -o $f.o || exit 1; done" % (" ".join(mods), driver, defines, ext))


def _recipe(variant):
    toolchain, template, defines, muldv = _SPEC[variant]
    build = [
        BuildStep("rm -rf mb && mkdir mb && cp include/*.h mb/ && "
                  "cp include/%s mb/mirdef.h" % template),
        BuildStep(_compile("{cc}", defines, m.C_MODULES, "c"), cwd="mb"),
        BuildStep(_compile("{cxx}", defines, m.CPP_MODULES, "cpp"),
                  cwd="mb"),
    ]
    if muldv:
        build.append(BuildStep(
            "cp ../source/%s mrmuldv.c && {cc} {archflag} -O2 -fPIC %s -I. "
            "-c mrmuldv.c -o mrmuldv.o" % (muldv, defines), cwd="mb"))
    build.append(BuildStep("{cxx} {archflag} -shared -o libmiracl.so *.o -lm",
                           cwd="mb"))
    return Recipe(
        family="MIRACL",
        version="%s-%s" % (m.DATE, variant),
        upstream=m.UPSTREAM,
        license=m.LICENSE,
        source=Source(git_url=m.UPSTREAM + ".git", git_ref=m.COMMIT),
        build=build,
        artifacts=[Artifact(path="mb/libmiracl.so", component="libmiracl.so")],
        toolchains=[toolchain],
        build_flags="-O2 -fPIC -shared, upstream template include/%s%s%s"
                    % (template, " " + defines if defines else "",
                       " + source/" + muldv if muldv else ""),
        notes=m.UNKNOWN + " This is the ELF build of the '%s' variant (%s) of "
              "upstream commit %s." % (variant, m.VARIANTS[variant], m.COMMIT),
    )


RECIPES = {"MIRACL_%s-%s_linux" % (m.DATE, v): _recipe(v) for v in _SPEC}

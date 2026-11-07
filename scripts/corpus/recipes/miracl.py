"""MIRACL (Shamus Software / CertiVox big-number and ECC library), MinGW.

See miracl_linux.py for why several variants exist and what is built; this
is the same module list built with the mingw-w64 cross compilers into a DLL.
**The variant that matches LockBit 3.0's keygen is unknown.**

Variants (MinGW):
  generic32  include/mirdef.h32 + -DMR_NOASM, x86. __int64 is native here.
  generic64  include/mirdef.mgw + -DMR_NOASM -Dmr_dltype=__int128, x64.
             mirdef.h64 is for LP64: it makes `long` the 64-bit word, and
             Windows is LLP64, so upstream ships mirdef.mgw (`long long`,
             MR_LBITS 32) for MinGW-w64 and that is the template used.
  asm64      include/mirdef.mgw + source/mrmuldv.g64 as mrmuldv.c: upstream's
             lib/mingw.bat.
There is no asm32 here: upstream's only MinGW script is the 64-bit one.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _miracl as m

_SPEC = {
    "generic32": ("mingw_x86", "mirdef.h32", "-DMR_NOASM", None),
    "generic64": ("mingw_x64", "mirdef.mgw",
                  "-DMR_NOASM -Dmr_dltype=__int128", None),
    "asm64": ("mingw_x64", "mirdef.mgw", "", "mrmuldv.g64"),
}


def _compile(driver, defines, mods, ext):
    return ("for f in %s; do %s -O2 %s -I. -c ../source/$f.%s -o $f.o || "
            "exit 1; done" % (" ".join(mods), driver, defines, ext))


def _recipe(variant):
    toolchain, template, defines, muldv = _SPEC[variant]
    build = [
        BuildStep("rm -rf mb && mkdir mb && cp include/*.h mb/ && "
                  "cp include/%s mb/mirdef.h" % template),
        BuildStep(_compile("{cc}", defines, m.C_MODULES, "c"), cwd="mb"),
        BuildStep(_compile("{cxx}", defines, m.CPP_MODULES, "cpp"), cwd="mb"),
    ]
    if muldv:
        build.append(BuildStep(
            "cp ../source/%s mrmuldv.c && {cc} -O2 %s -I. -c mrmuldv.c "
            "-o mrmuldv.o" % (muldv, defines), cwd="mb"))
    build.append(BuildStep("{cxx} -shared -o libmiracl.dll *.o -lm", cwd="mb"))
    return Recipe(
        family="MIRACL",
        version="%s-%s" % (m.DATE, variant),
        upstream=m.UPSTREAM,
        license=m.LICENSE,
        source=Source(git_url=m.UPSTREAM + ".git", git_ref=m.COMMIT),
        build=build,
        artifacts=[Artifact(path="mb/libmiracl.dll",
                            component="libmiracl.dll")],
        toolchains=[toolchain],
        build_flags="-O2 -shared, upstream template include/%s%s%s"
                    % (template, " " + defines if defines else "",
                       " + source/" + muldv if muldv else ""),
        notes=m.UNKNOWN + " This is the MinGW build of the '%s' variant (%s) "
              "of upstream commit %s." % (variant, m.VARIANTS[variant],
                                          m.COMMIT),
    )


RECIPES = {"MIRACL_%s-%s" % (m.DATE, v): _recipe(v) for v in _SPEC}

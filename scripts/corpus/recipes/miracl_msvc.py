"""MIRACL (Shamus Software / CertiVox big-number and ECC library), MSVC.

See miracl_linux.py for why several variants exist and what is built.
**The variant that matches LockBit 3.0's keygen is unknown.** This is the
side where upstream's own scripts (lib/ms32doit.bat, lib/ms64doit.bat) are
the reference, so the variants follow them:

  generic32  include/mirdef.h32 + /DMR_NOASM, x86.
  asm32      include/mirdef.h32 + source/mrmuldv.c32 as mrmuldv.c, x86:
             ms32doit.bat. The file uses MSVC inline `_asm`, which only
             x86 cl accepts.
  generic64  include/mirdef.w64 as upstream ships it + source/mrmuldv.w64 as
             mrmuldv.c, x64: ms64doit.bat. No assembly: muldvd/muldvd2 are the
             _umul128 intrinsic macros miracl.h selects when MR_WIN64 is
             defined, and mrmuldv.w64 is portable C. MR_NOASM is not added:
             it needs a double-width integer type and MSVC has no __int128.
             mirdef.h64 does not apply to Windows (LP64 `long`).

Build discipline: /MD, no /GL and no /LTCG; link /OPT:NOREF /OPT:NOICF
/Brepro /INCREMENTAL:NO. Every object is linked into a DLL that exports
nothing; names come from the PDB.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from . import _miracl as m

_SPEC = {
    "generic32": ("msvc_x86", "mirdef.h32", "/DMR_NOASM", None),
    "asm32": ("msvc_x86", "mirdef.h32", "", "mrmuldv.c32"),
    "generic64": ("msvc_x64", "mirdef.w64", "", "mrmuldv.w64"),
}

_CL = ("cl /nologo /c /O2 /MD /W3 /Zi /Fdmiracl.pdb /D_CRT_SECURE_NO_WARNINGS "
       "/I. %s")


def _recipe(variant):
    toolchain, template, defines, muldv = _SPEC[variant]
    c_files = " ".join("..\\source\\%s.c" % f for f in m.C_MODULES)
    cpp_files = " ".join("..\\source\\%s.cpp" % f for f in m.CPP_MODULES)
    build = [
        BuildStep("cmake -E remove_directory mb"),
        BuildStep("cmake -E copy_directory include mb"),
        BuildStep("cmake -E copy include\\%s mb\\mirdef.h" % template),
        BuildStep(_CL % (defines + " " + c_files), cwd="mb"),
        BuildStep(_CL % ("/EHsc " + defines + " " + cpp_files), cwd="mb"),
    ]
    if muldv:
        build.append(BuildStep("cmake -E copy ..\\source\\%s mrmuldv.c"
                               % muldv, cwd="mb"))
        build.append(BuildStep(_CL % (defines + " mrmuldv.c"), cwd="mb"))
    build.append(BuildStep(
        "link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
        "/OPT:NOICF /PDB:libmiracl.pdb /OUT:libmiracl.dll *.obj", cwd="mb"))
    build.append(BuildStep("dir", cwd="mb", allow_failure=True))
    return Recipe(
        family="MIRACL",
        version="%s-%s" % (m.DATE, variant),
        upstream=m.UPSTREAM,
        license=m.LICENSE,
        source=Source(git_url=m.UPSTREAM + ".git", git_ref=m.COMMIT),
        build=build,
        artifacts=[Artifact(path="mb/libmiracl.dll",
                            component="libmiracl.dll",
                            pdb="mb/libmiracl.pdb")],
        toolchains=[toolchain],
        build_flags="/O2 /MD /W3 /Zi, upstream template include/%s%s%s; "
                    "/DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF "
                    "/OPT:NOICF at link"
                    % (template, " " + defines if defines else "",
                       " + source/" + muldv if muldv else ""),
        notes=m.UNKNOWN + " This is the MSVC build of the '%s' variant (%s) "
              "of upstream commit %s." % (variant, m.VARIANTS[variant],
                                          m.COMMIT),
    )


RECIPES = {"MIRACL_%s-%s_msvc" % (m.DATE, v): _recipe(v) for v in _SPEC}

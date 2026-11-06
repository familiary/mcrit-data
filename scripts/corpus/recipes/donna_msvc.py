"""ed25519-donna and curve25519-donna built with MSVC (PROBE DRAFT)."""

from ..recipe import Artifact, BuildStep, Recipe, Source


_ED_COMMIT = "8757bd4cd209cb032853ece0ce413f122eef212c"
_CV_COMMIT = "28772f37a4b8a57ab9439b9e79b19f9abee686da"

_RNG = "{repo}/scripts/corpus/exercisers/ed25519_donna_rng.c"
_EDDEF = "{repo}/scripts/corpus/exercisers/ed25519_donna.def"
_CVDEF = "{repo}/scripts/corpus/exercisers/curve25519_donna.def"

_CL = "cl /nologo /c /O2 /MD /Zi"
_LINK = "link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF"


def _ed_steps(tag, extra, allow_failure=False):
    obj = "obj-" + tag
    name = "ed25519-donna" + ("-" + tag if tag != "generic" else "")
    return [
        BuildStep("if not exist %s mkdir %s" % (obj, obj)),
        BuildStep('%s /Fd%s.pdb /DED25519_REFHASH /DED25519_CUSTOMRANDOM %s /I. '
                  '/Fo%s\\ ed25519.c %s' % (_CL, name, extra, obj, _RNG),
                  allow_failure=allow_failure),
        BuildStep('%s /DEF:%s /PDB:%s.pdb /OUT:%s.dll %s\\ed25519.obj %s\\ed25519_donna_rng.obj'
                  % (_LINK, _EDDEF, name, name, obj, obj),
                  allow_failure=allow_failure),
    ]


def _ed25519():
    return Recipe(
        family="ed25519-donna",
        version="2015-03-16",
        upstream="https://github.com/floodyberry/ed25519-donna",
        license="public domain, as declared in the header of each source "
                "file (Andrew M.); the repository ships no licence file",
        source=Source(git_url="https://github.com/floodyberry/ed25519-donna.git",
                      git_ref=_ED_COMMIT),
        build=_ed_steps("generic", "") + _ed_steps("sse2", "/DED25519_SSE2", True)
              + [BuildStep("dir", allow_failure=True)],
        artifacts=[Artifact(path="ed25519-donna.dll",
                            component="ed25519-donna.dll",
                            pdb="ed25519-donna.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi -DED25519_REFHASH -DED25519_CUSTOMRANDOM",
        notes="probe",
    )


def _curve25519():
    return Recipe(
        family="curve25519-donna",
        version="1.3",
        upstream="https://github.com/agl/curve25519-donna",
        license="BSD-3-Clause, Copyright 2008 Google Inc.",
        source=Source(git_url="https://github.com/agl/curve25519-donna.git",
                      git_ref=_CV_COMMIT),
        build=[BuildStep("%s /Fdcurve25519-donna.pdb /Focurve25519-donna.obj "
                         "curve25519-donna.c" % _CL),
               BuildStep("%s /DEF:%s /PDB:curve25519-donna.pdb "
                         "/OUT:curve25519-donna.dll curve25519-donna.obj"
                         % (_LINK, _CVDEF))],
        artifacts=[Artifact(path="curve25519-donna.dll",
                            component="curve25519-donna.dll",
                            pdb="curve25519-donna.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        min_functions=6,
        build_flags="/O2 /MD /Zi",
        notes="probe",
    )


RECIPES = {
    "ed25519-donna_2015-03-16_msvc": _ed25519(),
    "curve25519-donna_1.3_msvc": _curve25519(),
}

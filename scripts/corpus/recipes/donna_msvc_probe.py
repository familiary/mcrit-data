"""SCRATCH PROBE - not for the PR."""
from ..recipe import Artifact, BuildStep, Recipe, Source
from .donna_msvc import _ed25519, _curve25519, _CL, _ED_COMMIT

def _p():
    r = _curve25519()
    r.version = "1.3-probe"
    r.build = r.build + [
        BuildStep("%s /Fdp64.pdb /Fop64.obj curve25519-donna-c64.c" % _CL, allow_failure=True),
        BuildStep("%s /Fdp64b.pdb /Fop64b.obj /Dinline=__inline curve25519-donna-c64.c" % _CL, allow_failure=True),
    ]
    return r

def _q():
    r = _ed25519()
    r.version = "2015-03-16-probe"
    r.build = r.build + [
        BuildStep("%s /Fdf1.pdb /DED25519_REFHASH /DED25519_CUSTOMRANDOM /DED25519_FORCE_32BIT /I. /Foobj-generic\\f1.obj ed25519.c" % _CL, allow_failure=True),
        BuildStep("%s /Fdf2.pdb /DED25519_REFHASH /DED25519_CUSTOMRANDOM /DED25519_FORCE_32BIT /DED25519_SSE2 /I. /Foobj-generic\\f2.obj ed25519.c" % _CL, allow_failure=True),
    ]
    return r

RECIPES = {"curve25519-donna_1.3_msvcprobe": _p(), "ed25519-donna_2015-03-16_msvcprobe": _q()}

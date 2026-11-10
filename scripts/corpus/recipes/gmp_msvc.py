"""GMP built with MSVC, beside the MinGW and Linux builds of the same release.

(Docstring completed after the runner build; see the corpus README.)
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .gmp import _VERSIONS


_BUILD = ("python {repo}/scripts/corpus/exercisers/gmp_msvc_build.py "
          "--arch {arch} --src . --work gmpbuild")


def _recipe(version):
    return Recipe(
        family="GMP",
        version=version,
        upstream="https://gmplib.org/",
        license="LGPL-3.0-or-later OR GPL-2.0-or-later (dual, licensee's choice)",
        source=Source(url="https://ftp.gnu.org/gnu/gmp/gmp-%s.tar.xz" % version,
                      sha256=_VERSIONS[version]),
        build=[BuildStep(_BUILD), BuildStep("dir gmpbuild", allow_failure=True)],
        artifacts=[Artifact(path="gmpbuild/libgmp-10.dll",
                            component="libgmp.dll",
                            pdb="gmpbuild/libgmp-10.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Z7, generic C only (no assembly, no --enable-fat), "
                    "config.h, gmp.h, gmp-mparam.h and the generated tables "
                    "produced from config.in, gmp-h.in and the gen-*.c programs; "
                    "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF at link; "
                    "exports generated from the objects",
        notes="No configure run (cl is not a supported GMP compiler): "
              "gmp_msvc_build.py reproduces what configure and make produce "
              "for the no-assembly configuration and compiles the source lists "
              "of Makefile.in and configure.ac with cl, unpatched. Portable C "
              "only, so none of GMP's assembly or fat dispatch is present. "
              "Built against the DLL runtime, so the MSVC C runtime stays "
              "attributed to data/MSVC. Pinned by the sha256 of a "
              "GPG-verified release tarball.",
    )


RECIPES = {"GMP_%s_msvc" % version: _recipe(version) for version in _VERSIONS}

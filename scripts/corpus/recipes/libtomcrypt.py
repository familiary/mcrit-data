"""LibTomCrypt - crypto toolkit with a long history of use in malware.

1.18.2 is realistically the only option: it is the newest tag and there has
been no 1.19.

The library needs LibTomMath for its bignum backend, and that code is linked
into the artefact - roughly 175 of its functions are mp_*, s_mp_* and
fast_mp_*. LibTomMath is therefore fetched as a pinned dependency so its
commit is verified and recorded, not cloned from a mutable tag inside a
build step.

Two honest limitations, both recorded in provenance rather than hidden:
upstream's makefile.mingw hardcodes -s on the DLL link line, so this artefact
is stripped and most function names come from the export table; and because
the CRT-glue filter matches on symbol names, it cannot act on the unnamed
functions, so MinGW runtime code remains in this sample.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_MINGW = ("make -j$(nproc) -f makefile.mingw CC={cc} AR={ar} RANLIB={ranlib} "
          "STRIP=:")


RECIPES = {
    "libtomcrypt_1.18.2": Recipe(
        family="libtomcrypt",
        version="1.18.2",
        upstream="https://github.com/libtom/libtomcrypt",
        # Upstream's LICENSE offers a choice of two, and neither is the
        # Unlicense: "LibTomCrypt is public domain" or WTFPL v2.
        license="public domain / WTFPL-2.0 (dual, licensee's choice)",
        source=Source(git_url="https://github.com/libtom/libtomcrypt.git",
                      git_ref="v1.18.2"),
        extra_sources={"libtommath": Source(
            git_url="https://github.com/libtom/libtommath.git",
            git_ref="v1.3.0")},
        build=[
            BuildStep("cp -r {libtommath} ltm"),
            BuildStep(_MINGW + ' CFLAGS="-O2"', cwd="ltm"),
            BuildStep(_MINGW + ' CFLAGS="-O2 -DUSE_LTM -DLTM_DESC -Iltm" '
                      'EXTRALIBS="ltm/libtommath.a" libtomcrypt.dll'),
        ],
        artifacts=[Artifact(path="libtomcrypt.dll", component="libtomcrypt.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 (both libtomcrypt and the bundled libtommath)",
        notes="Statically links LibTomMath 1.3.0, so roughly 175 of this "
              "sample's functions are mp_*/s_mp_*/fast_mp_* and belong to that "
              "project. Upstream's makefile.mingw forces -s, so the sample is "
              "stripped; with most functions unnamed the CRT-glue filter "
              "cannot act on them and MinGW runtime code remains present.",
        # Stripped by upstream's link line, so the symbol guard cannot apply.
        min_named_ratio=0,
    ),
}

"""LibTomCrypt - crypto toolkit with a long history of use in malware.

1.18.2 is realistically the only option: it is the newest tag and there has
been no 1.19. The library needs LibTomMath for its bignum backend, which is
built first inside the same tree.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_MINGW = ("make -j$(nproc) -f makefile.mingw CC={cc} AR={ar} RANLIB={ranlib} "
          "STRIP=:")


RECIPES = {
    "libtomcrypt_1.18.2": Recipe(
        family="libtomcrypt",
        version="1.18.2",
        upstream="https://github.com/libtom/libtomcrypt",
        license="public domain / Unlicense",
        source=Source(git_url="https://github.com/libtom/libtomcrypt.git",
                      git_ref="v1.18.2"),
        build=[
            # LibTomMath is a hard dependency of the MPI backend; fetched into
            # the tree so the whole build stays inside one source root.
            BuildStep("git clone -q --depth 1 -b v1.3.0 "
                      "https://github.com/libtom/libtommath.git ltm"),
            BuildStep(_MINGW, cwd="ltm"),
            BuildStep(_MINGW + ' CFLAGS="-O2 -DUSE_LTM -DLTM_DESC -Iltm" '
                      'EXTRALIBS="ltm/libtommath.a" libtomcrypt.dll'),
        ],
        artifacts=[Artifact(path="libtomcrypt.dll", component="libtomcrypt.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2",
        notes="makefile.mingw hardcodes -s on the DLL link line, so this "
              "artefact is stripped; it exports everything, so names still "
              "come from the export table rather than the symbol table.",
        # Stripped by upstream's link line, so the symbol guard cannot apply.
        min_named_ratio=0,
    ),
}

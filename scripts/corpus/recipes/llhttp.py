"""llhttp - nodejs/llhttp, the HTTP/1.x parser inside Node.js, undici and XMRig.

No coverage exists in the corpus today: there is no HTTP parser family, and
the libuv, libevent and libcurl recipes do not vendor one. This recipe is
here to close that category gap, and the honest statement of what it is worth
is that the case is structural rather than measured. Nothing in the corpus
has been checked against a sample that contains llhttp; the claim is only
that XMRig vendors it and that a miner or loader embedding it is otherwise
unrepresented. Upstream publishes no checksums of its own; 9.3.0, the
version the tracker names, is pinned by the SHA-256 of a release tarball (see
below), the neighbouring versions by their git tags.

llhttp's parser is *generated* (by llparse, TypeScript), and the sources a
build needs are not in the development tree. The ``release/vX.Y.Z`` tag is
the exception: it is a commit holding only the generated ``src/llhttp.c``,
``src/api.c``, ``src/http.c`` and ``include/llhttp.h`` plus ``CMakeLists.txt``,
and that is what is built. No npm, no llparse, nothing patched.

The 9.3.0 tarball. The v9.3.0 release on GitHub has no uploaded assets, only
the two archives GitHub generates of the tag v9.3.0 (commit 36151b9), and
that tag is the generator tree: it has no ``src/llhttp.c`` and no
``include/llhttp.h`` (llparse writes both at release time), and its
``src/native/api.c`` and ``src/native/http.c`` are the same blobs as the
release tag's ``src/api.c`` and ``src/http.c``. It cannot be built without
running llparse. The generated sources exist only on the tag release/v9.3.0
(commit 86b83a5, tree 2c10300), so the pin is GitHub's archive of that tag,
``archive/refs/tags/release/v9.3.0.tar.gz``, by SHA-256: the same commit the
git pin named, as a file with a digest. The digest was established with
``git archive --format=tar --prefix=llhttp-release-v9.3.0/ release/v9.3.0 |
gzip -n``, which reproduces GitHub's archives byte for byte: the same command
gives Homebrew's pinned SHA-256 of the release/v9.4.3 archive
(1eb813c7...9f36c39) and vcpkg's pinned SHA-512 of the release/v9.3.1
archive. Built from the tarball, the 9.3.0 images are PicHash-identical to
the ones built from the git tag on both architectures: the same 124 (x86)
and 136 (x64) functions, the same name, instruction count and PicHash for
every one, and the same 114 and 109 removed. The DLLs' own digests differ
only because -g writes the absolute build directory into the debug
information, and the unpacked tarball sits at a different path from the
checkout. So the committed images are the ones built from the git tag, and
only the source pin in their provenance was changed to the tarball (their
sha256 field is still the digest of the DLL that was disassembled).

Built with upstream's own CMake rather than a direct ``-shared`` compile of
the three files. The two produce the same code - the CMake target is just
those three files at C99 - but CMake is what upstream documents, it is what
the sibling recipes do, and it records the flags upstream actually chose
(its default build type is RelWithDebInfo, ``-O2 -g -DNDEBUG``, which is kept
rather than overridden to Release). One cosmetic side effect: CMake's
``configure_file`` writes ``libllhttp.pc`` into the source tree.

One version, measured rather than assumed. Counting functions of at least 10
instructions, 9.3.0 and 9.3.1 are PicHash-identical on both architectures
(44 of 44 on x86, 30 of 30 on x64), and 9.4.3 shares 42 of 44 and 28 of 30
with 9.3.0; the two that differ are the state machine ``llhttp__internal__run``
and ``llhttp__internal_init``. 9.2.1 shares 34 of
41 (x86) and 23 of 29 (x64) with 9.3.0; what differs there is ``run`` again
(5140 instructions against 5349 on x64), ``llhttp_errno_name`` (81 against 98) and a handful of 12 to 28 instruction callbacks. So the
non-shared part is one very large function and a few small ones, not a second
body of code; a matcher is served by 9.3.0 plus MinHash for ``run``, and a
second version was not added. 9.2.1 is the candidate if one is wanted later.

The older joyent/http-parser lineage (a single ``http_parser_execute`` switch,
the ancestor of llhttp's API and still vendored by older software) is a
separate codebase with a different function structure. It was not built and
not measured; llhttp's ``llhttp_*`` entry points are a different surface from
``http_parser_*``, so nothing here stands in for it.

Function count against the floor of eight, measured: the generated state
machine does not compile to a few large functions. It is one 5349 instruction
function (``llhttp__internal__run``, 5493 on x86) plus roughly 120 small
``llhttp__internal__*`` and ``llhttp_*`` helpers and callbacks. After the
runtime baseline removes 109 (x64) and 114 (x86) functions, the artefacts
hold 136 and 124 functions, of which 123 on each architecture are llhttp's
own by name; 30 (x64) and 44 (x86) reach 10 instructions. ``min_functions``
is not used. The remainder is one unnamed 15-instruction ``___chkstk_ms``
stack probe (the known libgcc gap) and, on x64, 12 unnamed one-instruction
import thunks.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CMAKE = ("cmake -S . -B build-{arch} -DCMAKE_SYSTEM_NAME=Windows "
          "-DCMAKE_C_COMPILER={cc} -DCMAKE_FIND_ROOT_PATH=/usr/{host} "
          "-DBUILD_SHARED_LIBS=ON")


_TARBALL_9_3_0 = Source(
    url="https://github.com/nodejs/llhttp/archive/refs/tags/release/"
        "v9.3.0.tar.gz",
    sha256="1a2b45cb8dda7082b307d336607023aa65549d6f060da1d246b1313da22b685a")


def _llhttp(version, git_ref, source=None):
    return Recipe(
        family="llhttp",
        version=version,
        upstream="https://github.com/nodejs/llhttp",
        license="MIT",
        source=source or Source(git_url="https://github.com/nodejs/llhttp.git",
                                git_ref=git_ref),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch} -j$(nproc)"),
        ],
        artifacts=[Artifact(path="build-{arch}/libllhttp.dll",
                            component="libllhttp.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -g -DNDEBUG (CMake RelWithDebInfo, upstream default), "
                    "-std=gnu99",
        notes="Pre-generated C from the release/v%s tag (llhttp.c, api.c, "
              "http.c); the llparse toolchain is not run." % version,
    )


RECIPES = {
    # The release tarball of the tag release/v9.3.0 (commit 86b83a5).
    "llhttp_9.3.0": _llhttp("9.3.0", "release/v9.3.0", _TARBALL_9_3_0),
}

# The neighbouring releases the first revision built only to measure and
# deleted: 9.2.1 (34/41 x86 and 23/29 x64 hashes of ten instructions or more
# shared with 9.3.0) and 9.4.3 (42/44 and 28/30). 9.3.1 is not added: built
# again in the second pass, its images are PicHash-identical, every function
# at every size, to 9.3.0's on both architectures (124 + 114 = 238 / 136 +
# 109 = 245, the same counts), so it would add nothing.
RECIPES["llhttp_9.2.1"] = _llhttp("9.2.1", "release/v9.2.1")
RECIPES["llhttp_9.4.3"] = _llhttp("9.4.3", "release/v9.4.3")

# Measured (kept + removed = total, no exclusions; ten-instruction PicHashes
# in brackets): 9.2.1 x86 121 + 114 = 235 (41), x64 133 + 109 = 242 (29);
# 9.4.3 x86 126 + 114 = 240 (44), x64 138 + 109 = 247 (30). 9.2.1 shares 34
# of 41 / 23 of 29 with 9.4.3 and 9.4.3 42 of 44 / 28 of 30 with 9.3.0, so
# neither is a duplicate.

"""jemalloc - allocator with a real, if niche, Windows presence.

Turns up in Firefox-derived code and in some game and anti-cheat stacks.
The C++ wrapper is disabled: it adds libstdc++ surface without adding
allocator code, and libstdc++ belongs to the MinGW family, not here.

Four releases, chosen where the allocator was rebuilt rather than by recency.
Issue #10 records jemalloc as partial for two reasons, and this addresses the
one that can be addressed here: it was a single version.

  * **3.6.0** is the last of the 3.x line and the generation Firefox carried
    for years. Its internals are chunk-and-run based - ``arena_run_t``,
    ``arena_chunk_t``, the bitmap-per-run allocator - which the 4.x extent
    rewrite replaced wholesale, so nothing below the public entry points
    looks like anything later.
  * **4.5.0** is the last of 4.x. It has the extent machinery but not the
    5.x background thread, the new arena decay or the rtree rewrite.
  * **5.2.1** is what an enormous amount of shipped software links: the
    generation Rust's allocator, Redis and much else standardised on before
    5.3.
  * **5.3.0** and **5.4.0** are the current line, kept as a pair because
    5.4.0 is recent enough that most binaries in the field are still 5.3.

MSVC is still absent and the reason is not a preference. ``msvc/ReadMe.txt``
step 5 requires ``sh -c "CC=cl ./autogen.sh"`` before the solution can be
opened, and ``include/jemalloc/`` holds only ``.h.in`` templates until
autoconf and configure have run - the vcxproj includes headers that do not
exist yet. ``scripts/corpus/msvc-coverage-survey.md`` records this, and it was
rechecked here against the release tarball rather than the git tag, in case
the tarball shipped a generated ``configure`` the way many autotools projects
do: ``jemalloc-5.3.0.tar.bz2`` ships ``configure.ac`` and ``autogen.sh`` and
no ``configure`` either. So an MSVC jemalloc needs autoconf and a POSIX shell
on windows-2022, which is a runner-image change of the same class as the nasm
step, for a family that survey rates low-medium value.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# jemalloc 3.6.0 determines the page size by running a test program, which a
# cross build cannot do: "checking STATIC_PAGE_SHIFT... configure: error:
# cannot run test program while cross compiling". configure.ac wraps it in
# AC_CACHE_CHECK([STATIC_PAGE_SHIFT], [je_cv_static_page_shift], ...), so
# priming that cache variable skips the run test. 12 is 4 KiB, which is the
# page size on Windows for both architectures. Later releases derive it
# without running anything and ignore the variable.
_PAGE_SHIFT = {"je_cv_static_page_shift": "12"}

# Options 3.6.0 does not have; its configure warns they are unrecognized.
_MODERN = " --disable-cxx --enable-shared --disable-static"


def _jemalloc(version, notes="", configure_extra="", env=None):
    return Recipe(
        family="jemalloc",
        version=version,
        upstream="https://github.com/jemalloc/jemalloc",
        license="BSD-2-Clause",
        source=Source(git_url="https://github.com/jemalloc/jemalloc.git",
                      git_ref=version),
        build=[
            BuildStep("./autogen.sh --host={host}" + configure_extra,
                      env=env or {}),
            BuildStep("make -j$(nproc) build_lib_shared"),
        ],
        artifacts=[Artifact(path="lib/jemalloc.dll", component="jemalloc.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O3 (upstream default)",
        requires=["autoconf"],
        notes=notes,
    )


RECIPES = {
    # 3.6.0 predates --disable-cxx, --enable-shared and --disable-static, and
    # its configure warns they are unrecognized, so they are not passed.
    "jemalloc_3.6.0": _jemalloc(
        "3.6.0", env=_PAGE_SHIFT, notes=
        "Last of the 3.x line and the generation Firefox carried for years. "
        "Chunk-and-run internals - arena_run_t, arena_chunk_t, a bitmap per "
        "run - which the 4.x extent rewrite replaced wholesale, so below the "
        "public entry points this shares almost nothing with 4.x or 5.x."),
    "jemalloc_4.5.0": _jemalloc(
        "4.5.0", configure_extra=_MODERN, notes=
        "Last of the 4.x line: the extent machinery is in, but not the 5.x "
        "background thread, arena decay or rtree rewrite."),
    "jemalloc_5.2.1": _jemalloc(
        "5.2.1", configure_extra=_MODERN, notes=
        "The 5.x generation an enormous amount of shipped software links - "
        "what Rust's allocator, Redis and much else standardised on before "
        "5.3."),
    "jemalloc_5.3.0": _jemalloc(
        "5.3.0", configure_extra=_MODERN, notes=
        "The current line, and still what most binaries in the field carry."),
    "jemalloc_5.4.0": _jemalloc(
        "5.4.0", configure_extra=_MODERN, notes= "Current release, kept beside 5.3.0 rather than replacing "
        "it, because 5.4.0 is recent enough that 5.3 is what is in the "
        "field."),
}

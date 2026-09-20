"""q3vm - the standalone Quake 3 QVM interpreter (mcrit-data issue #2).

vm.c is explicitly written to be dropped into other projects and is forked
from ioquake3, so the same code shape turns up in Quake3-engine derivatives
and in anything that embeds a QVM sandbox.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


def _q3vm(version, git_ref):
    return Recipe(
        family="q3vm",
        version=version,
        upstream="https://github.com/jnz/q3vm",
        license="GPL-2.0 (inherited from the Quake III Arena source release)",
        source=Source(git_url="https://github.com/jnz/q3vm.git", git_ref=git_ref),
        # The default target also builds LCC and assembles bytecode with host
        # tools, so the VM target has to be named explicitly. LINK_FLAGS is
        # passed because upstream exports LINKFLAGS but links with LINK_FLAGS,
        # which silently drops --gc-sections when cross-compiling from Linux.
        build=[
            BuildStep("make clean", allow_failure=True),
            BuildStep("make q3vm TOOLCHAIN={prefix} LINK_FLAGS=-Wl,--gc-sections"),
        ],
        # mingw-w64 appends .exe even though the makefile links to "q3vm".
        artifacts=[Artifact(path="q3vm.exe", component="q3vm.exe", is_library=False)],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="-O2 -std=c89 -fno-crossjumping (upstream Makefile)",
        notes="GCC builds use computed-goto dispatch; the in-tree MSVC solution "
              "produces switch-based dispatch, which is not covered here.",
    )


RECIPES = {
    # The only released version, and what any tarball grab since 2018 carries.
    "q3vm_1.3.1": _q3vm("1.3.1", "v1.3.1"),
    # 31 commits and ~140 changed lines of vm.c/vm.h past v1.3.1, including
    # opcode handling changes - genuinely different code, not a rebuild.
    "q3vm_2026-03-06": _q3vm("2026-03-06",
                             "df042e22febcd2851ff26db570f89d04899ca111"),
}

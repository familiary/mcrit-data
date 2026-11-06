"""FreshyCalls (crummie5) - sort-by-virtual-address SSN resolution.

The technique SysWhispers4 names ``--resolve freshycalls`` and credits here,
in its original C++ form. Rather than carrying a table of syscall numbers or
reading them out of a possibly-hooked stub, it collects every ``Nt*`` export
of ntdll, sorts them by virtual address, and takes each one's service number
from its position in that order - which holds because the kernel assigns
numbers in the order the stubs appear in the image. ``ExtractStubs`` is that
parse and sort, 302 instructions at -O2, and it is what an implant vendoring
this carries.

The project is four headers and two translation units with no build system
of any kind - no CMakeLists, no makefile, no project file - so the compile
line here is this recipe's, not upstream's. Its entry points are variadic
templates on a singleton class (``CallSyscall``, ``DirectCallSyscall``), so
``exercisers/freshycalls.cpp`` instantiates them; compiling syscall.cpp and
utils.cpp alone would emit the non-template members only.

Three things the command line has to supply, each found by building, and
none of them a change to upstream:

* **``-include intrin.h``**. syscall.hpp takes a ``__GNUC__`` branch that
  includes ``<psdk_inc/intrin-impl.h>``, which does not declare the
  intrinsics it then uses: "``__readgsqword`` was not declared in this
  scope".
* **``-I`` a case shim for ``Windows.h``**. utils.cpp includes the capital-W
  spelling, which exists on MSVC's case-insensitive filesystem and not in a
  mingw-w64 sysroot on Linux. ``exercisers/win_case_compat/Windows.h``
  forwards to ``<windows.h>``; the same obstacle is recorded in
  wow64pp.cpp's docstring, which solved it by editing its own include.
* **``-DUNICODE -D_UNICODE``**. utils.cpp passes a wide literal to
  ``FormatMessage``, which is the ``-W`` form only when UNICODE is defined;
  without it GCC reports "cannot convert 'const wchar_t*' to 'LPCSTR'". An
  MSVC project defines it by default, which is why upstream never hit this.

**x64 only**, and not by this recipe's choice: syscall.hpp opens with
``#if !defined(__x86_64) && !defined(_M_AMD64)`` / ``#error Only x64
compilations are supported``.

**``-shared-libgcc``** and no ``-static-libstdc++``, per the corpus's rule
for C++ samples: linking libstdc++ statically would pull roughly 13,500 of
its functions into the artefact under this family's name.

Measured: 173 functions, 156 named, of which seven of ten instructions or
more are the project's own - ``ExtractStubs`` at 302, ``GetSyscallNumber``
at 186, ``utils::GetErrorMessage`` at 91, ``GetStubAddr`` at 59 and two
``utils`` string helpers - plus the exerciser. The remainder is libstdc++
``std::map`` and ``std::string`` instantiation, which the measured glue
baseline removes.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_EX = "{repo}/scripts/corpus/exercisers"
_BUILD = ("{cxx} -std=c++17 -O2 -shared -I. -I%s/win_case_compat "
          "-include intrin.h -DUNICODE -D_UNICODE "
          "-o freshycalls.dll %s/freshycalls.cpp syscall.cpp utils.cpp "
          # mingw's ld stamps a PE timestamp and picks a random DLL
          # ImageBase, either of which makes the recorded sha256 change on
          # every rebuild. See exercisers/sw4_build.py:repro_flags.
          "-shared-libgcc -Wl,--no-insert-timestamp "
          "-Wl,--disable-auto-image-base -Wl,--image-base,0x180000000"
          % (_EX, _EX))


RECIPES = {
    "FreshyCalls_2022-09-01": Recipe(
        family="FreshyCalls",
        version="2022-09-01",
        upstream="https://github.com/crummie5/FreshyCalls",
        license="MPL-2.0",
        source=Source(git_url="https://github.com/crummie5/FreshyCalls.git",
                      git_ref="112bdf0db63a5f7104ba5243af6a672bc098a1ad"),
        build=[BuildStep(_BUILD)],
        artifacts=[Artifact(path="freshycalls.dll", component="freshycalls.dll")],
        # x64 only; syscall.hpp #errors on anything else.
        toolchains=["mingw_x64"],
        build_flags=("-std=c++17 -O2 -shared -shared-libgcc, "
                     "-include intrin.h, -DUNICODE -D_UNICODE, "
                     "-Wl,--no-insert-timestamp "
                     "-Wl,--disable-auto-image-base "
                     "-Wl,--image-base,0x180000000"),
        notes="Built from an exerciser translation unit: the project has no "
              "build system and its callers are variadic templates, so "
              "nothing of the interesting half exists in a binary until "
              "something instantiates them. Coverage is every entry point "
              "the Syscall class exposes - CallSyscall and DirectCallSyscall "
              "at three arities each, because the variadic template emits a "
              "different stub signature per argument count, plus "
              "GetSyscallNumber, GetStubAddr and the get_instance path that "
              "runs ExtractStubs and ExtractSyscallsNumbers. Nothing is ever "
              "run; the arguments are whatever makes each overload resolve.",
    ),
}

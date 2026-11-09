"""Build the header-only ADVobfuscator exerciser for one compiler target."""

from __future__ import annotations

import argparse
import os
import shutil
import shlex
import subprocess
from pathlib import Path


# Both snapshots seed their pseudo-random generator from __TIME__
# (include/advobfuscator/random.h and Lib/MetaRandom.h: hh:mm:ss, seconds
# included), so every unpinned build differs from the last by the key schedule
# of every obfuscated literal and by a few percent of its functions. The seed is
# pinned through SOURCE_DATE_EPOCH, which GCC (7 and later) and cl honour for
# __TIME__ and __DATE__: 1700000000 is 2023-11-14 22:13:20 UTC, so __TIME__ is
# "22:13:20". A probe translation unit is compiled first and the pinned string
# must be in the object, so a compiler that ignores the variable fails the
# build instead of producing an image that only looks pinned.
PINNED_EPOCH = "1700000000"
PINNED_TIME = b"22:13:20"


def _pinned_env() -> dict:
    env = dict(os.environ)
    env["SOURCE_DATE_EPOCH"] = PINNED_EPOCH
    env["TZ"] = "UTC"
    return env


def _probe_pins(probe_command: list[str], obj: Path, root: Path,
                extra: list[str]) -> bool:
    probe = root / "build" / "time_probe.cpp"
    probe.write_text("extern const char corpus_time[];\n"
                     "const char corpus_time[] = __TIME__;\n")
    if obj.exists():
        obj.unlink()
    result = subprocess.run(probe_command + extra + [str(probe)], cwd=root,
                            env=_pinned_env())
    return result.returncode == 0 and PINNED_TIME in obj.read_bytes()


def _msvc_pin_flags(probe_command: list[str], obj: Path, root: Path) -> list[str]:
    """The cl flags that pin __TIME__, found by probing, or [] if none does.

    cl (MSVC 14.4 on the windows-2022 runner) was measured not to honour
    SOURCE_DATE_EPOCH, so the alternatives are tried in turn: a command-line
    definition and a forced-include header that redefines the macro. A
    candidate is accepted only if the pinned string is in the probe object.
    """
    header = root / "build" / "pin_time.h"
    header.write_text('#undef __TIME__\n#define __TIME__ "%s"\n'
                      % PINNED_TIME.decode())
    candidates = [["/D__TIME__=\"%s\"" % PINNED_TIME.decode()],
                  ["/FI" + str(header)]]
    for flags in candidates:
        if _probe_pins(probe_command, obj, root, flags):
            return flags
    return []


def _check_pinned(probe_command: list[str], obj: Path, root: Path,
                  msvc: bool = False) -> list[str]:
    """Verify that __TIME__ is pinned; return extra compiler flags if needed.

    GCC honours SOURCE_DATE_EPOCH and the build fails if it somehow does not.
    cl does not, so for cl the flags that do pin it are searched for; if there
    are none the build proceeds unpinned and says so, because the alternative
    is no MSVC image at all.
    """
    if _probe_pins(probe_command, obj, root, []):
        print("pinned __TIME__ = %s (SOURCE_DATE_EPOCH)"
              % PINNED_TIME.decode(), flush=True)
        return []
    if not msvc:
        raise SystemExit("SOURCE_DATE_EPOCH=%s was not honoured for __TIME__ "
                         "by %s; the build would not be reproducible"
                         % (PINNED_EPOCH, probe_command[0]))
    flags = _msvc_pin_flags(probe_command, obj, root)
    if flags:
        print("pinned __TIME__ = %s (cl %s)" % (PINNED_TIME.decode(),
                                                 " ".join(flags)), flush=True)
    else:
        print("NOT PINNED: cl ignores SOURCE_DATE_EPOCH, /D__TIME__ and a "
              "forced-include redefinition; __TIME__ is the build time and "
              "this image is not reproducible", flush=True)
    return flags


def _run(command: list[str], root: Path) -> None:
    print("+ " + subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=root, check=True, env=_pinned_env())


# GCC 13 cannot deduce the class-type template parameter of the C++20
# string-literal operators from the literal (class template argument deduction
# for a non-type template parameter): "no matching function for call to
# operator""_obf_bytes<...>()" and the same for _obf. The MinGW current build
# therefore compiles a patched COPY of the two headers (the upstream checkout
# is not modified) whose literal operators take a structural character-array
# wrapper and construct the unchanged ObfuscatedBytes/ObfuscatedString from it.
_LITERAL_PATCHES = {
    "bytes.h": (
        """  template<ObfuscatedBytes block>
  consteval auto operator""_obf_bytes() { return block; }""",
        """  template<std::size_t N>
  struct ObfBytesLiteral {
    constexpr ObfBytesLiteral(const char (&str)[N]) { for(std::size_t i = 0; i < N; ++i) chars[i] = str[i]; }
    char chars[N];
  };

  template<ObfBytesLiteral lit>
  consteval auto operator""_obf_bytes() { return ObfuscatedBytes<sizeof(lit.chars)>(lit.chars); }"""),
    "string.h": (
        """  template<ObfuscatedString str>
  consteval auto operator ""_obf() { return str; }""",
        """  template<std::size_t N>
  struct ObfStringLiteral {
    constexpr ObfStringLiteral(const char (&str)[N]) { for(std::size_t i = 0; i < N; ++i) chars[i] = str[i]; }
    char chars[N];
  };

  template<ObfStringLiteral lit>
  consteval auto operator ""_obf() { return ObfuscatedString<sizeof(lit.chars)>(lit.chars); }"""),
}


def _patched_include(root: Path) -> Path:
    target = root / "build" / "include-gcc13"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(root / "include", target)
    for name, (old, new) in _LITERAL_PATCHES.items():
        path = target / "advobfuscator" / name
        text = path.read_text()
        if old not in text:
            raise SystemExit("literal-operator patch does not apply to %s" % name)
        path.write_text(text.replace(old, new, 1))
    return target


def build(args: argparse.Namespace) -> Path:
    root = Path.cwd()
    build_dir = root / "build"
    build_dir.mkdir(exist_ok=True)
    source = Path(args.repo) / "scripts/corpus/exercisers/advobfuscator.cpp"
    legacy = args.mode == "legacy"
    bitness_flag = ["-m%d" % args.bitness] if args.flavor == "linux" else []
    standard = "/std:c++20" if not legacy else "/std:c++14"
    gcc_standard = "-std=c++20" if not legacy else "-std=c++14"
    version = "2020-06-26" if legacy else "2026-10-27"
    extension = "dll" if args.flavor in ("mingw", "msvc") else "so"
    output = build_dir / ("advobfuscator-%s-%s.%s" %
                          (args.mode, args.arch, extension))

    if args.flavor == "msvc":
        obj = build_dir / ("advobfuscator-%s-%s.obj" % (args.mode, args.arch))
        compiler_pdb = build_dir / ("advobfuscator-%s-%s-cc.pdb" %
                                    (args.mode, args.arch))
        linker_pdb = build_dir / ("advobfuscator-%s-%s.pdb" %
                                  (args.mode, args.arch))
        probe_obj = build_dir / "time_probe.obj"
        pin_flags = _check_pinned(
            [args.cxx, "/nologo", "/TP", "/c", "/Fo" + str(probe_obj),
             "/Fd" + str(build_dir / "time_probe.pdb")], probe_obj, root,
            msvc=True)
        optimization = ["/Od", "/Ob0"] if not legacy else ["/O2", "/Ob0"]
        command = [args.cxx, "/nologo", "/TP", "/c", standard,
                   *optimization, "/MD", "/Zi", "/GL-", "/W3",
                   "/I" + str(Path(args.repo) / "scripts/corpus/exercisers")]
        if legacy:
            command += ["/DADV_LEGACY", "/I" + str(root / "Lib")]
        else:
            command.append("/I" + str(root / "include"))
        command += pin_flags
        command += ["/Fo" + str(obj), "/Fd" + str(compiler_pdb), str(source)]
        _run(command, root)
        _run(["link", "/DLL", "/DEBUG", "/OPT:NOREF", "/OPT:NOICF",
              "/Brepro", "/INCREMENTAL:NO", "/OUT:" + str(output),
              "/PDB:" + str(linker_pdb), str(obj)], root)
        return output

    compiler = shlex.split(args.cxx)
    command = compiler + bitness_flag + [gcc_standard,
                                          "-O0" if not legacy else "-O2"]
    if legacy:
        command.append("-fno-inline")
    if args.flavor == "linux":
        command += ["-fPIC", "-shared"]
    else:
        command += ["-shared", "-Wl,--no-insert-timestamp"]
    command += ["-I" + str(Path(args.repo) / "scripts/corpus/exercisers")]
    if legacy:
        command += ["-DADV_LEGACY", "-I" + str(root / "Lib")]
    else:
        include = (_patched_include(root) if args.flavor == "mingw"
                   else root / "include")
        command.append("-I" + str(include))
    probe_obj = build_dir / "time_probe.o"
    _check_pinned(compiler + bitness_flag + ["-c", "-o", str(probe_obj)],
                  probe_obj, root)
    command += ["-o", str(output), str(source)]
    _run(command, root)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("current", "legacy"), required=True)
    parser.add_argument("--flavor", choices=("linux", "mingw", "msvc"), required=True)
    parser.add_argument("--arch", choices=("x86", "x64"), required=True)
    parser.add_argument("--bitness", type=int, choices=(32, 64), required=True)
    parser.add_argument("--cxx", required=True)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()
    result = build(args)
    print("built %s" % result.relative_to(Path.cwd()), flush=True)


if __name__ == "__main__":
    main()

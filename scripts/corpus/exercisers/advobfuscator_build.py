"""Build the header-only ADVobfuscator exerciser for one compiler target."""

from __future__ import annotations

import argparse
import shutil
import shlex
import subprocess
from pathlib import Path


def _run(command: list[str], root: Path) -> None:
    print("+ " + subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=root, check=True)


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
        optimization = ["/Od", "/Ob0"] if not legacy else ["/O2", "/Ob0"]
        command = [args.cxx, "/nologo", "/TP", "/c", standard,
                   *optimization, "/MD", "/Zi", "/GL-", "/W3",
                   "/I" + str(Path(args.repo) / "scripts/corpus/exercisers")]
        if legacy:
            command += ["/DADV_LEGACY", "/I" + str(root / "Lib")]
        else:
            command.append("/I" + str(root / "include"))
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

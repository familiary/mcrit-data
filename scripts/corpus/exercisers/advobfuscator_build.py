"""Build the header-only ADVobfuscator exerciser for one compiler target."""

from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path


def _run(command: list[str], root: Path) -> None:
    print("+ " + subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=root, check=True)


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
        command.append("-I" + str(root / "include"))
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

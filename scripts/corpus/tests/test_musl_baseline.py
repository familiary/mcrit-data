"""The musl toolchain and its glue baseline.

The first half needs no compiler: it pins down what kind="musl" changes and
what it leaves alone. The second half builds the baseline with the real
musl.cc compilers and is skipped on a host that does not have them on PATH
(the CI runner does not), so a green run on such a host says nothing about
the measurement - run it where exercisers/fetch_musl_toolchain.sh has been.

    python -m pytest scripts/corpus/tests/test_musl_baseline.py
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from corpus import baseline, toolchain


def _musl_toolchain(arch="x64", bitness=64):
    triple = toolchain.MUSL_PINS[arch]["triple"]
    return toolchain._musl(arch, bitness, triple, "11")


class MuslToolchainShapeTest(unittest.TestCase):
    def test_the_pins_are_complete(self):
        for arch, pin in toolchain.MUSL_PINS.items():
            self.assertRegex(pin["sha256"], r"^[0-9a-f]{64}$", arch)
            self.assertTrue(pin["url"].startswith("https://musl.cc/"), arch)
            self.assertTrue(pin["url"].endswith(pin["name"] + ".tgz"), arch)
            self.assertTrue(pin["name"].count(pin["triple"]) == 1, arch)

    def test_the_slug_alias_and_container(self):
        t = _musl_toolchain()
        self.assertEqual(t.id, "musl11_x64")
        self.assertEqual(t.short_id, "musl11")
        self.assertEqual(toolchain.canonical_alias("musl11_x64"), "musl_x64")
        self.assertEqual(toolchain.canonical_alias("musl_x86"), "musl_x86")
        self.assertEqual(toolchain.image_format("musl11_x64"), "ELF")
        self.assertEqual(toolchain.image_format("musl_x86"), "ELF")

    def test_the_other_toolchains_keep_their_container(self):
        self.assertEqual(toolchain.image_format("gcc13_x64"), "ELF")
        self.assertEqual(toolchain.image_format("mingw13_x64"), "PE")
        self.assertEqual(toolchain.image_format("msvc143_x86"), "PE")

    def test_the_probe_is_a_static_executable_without_an_empty_argument(self):
        command = _musl_toolchain().probe_command("cc", "p.c", "out", False)
        self.assertEqual(command, ["cc", "-O2", "-o", "out", "p.c", "-static"])
        self.assertNotIn("", command)

    def test_the_environment_and_placeholders(self):
        env = _musl_toolchain("x86", 32).build_env()
        self.assertEqual(env["CC"], "i686-linux-musl-gcc")
        self.assertEqual(env["AR"], "i686-linux-musl-gcc-ar")
        self.assertNotIn("WINDRES", env)
        self.assertEqual(env["STRIP"], "true")
        placeholders = _musl_toolchain("x86", 32).placeholders()
        self.assertEqual(placeholders["host"], "i686-linux-musl")
        self.assertEqual(placeholders["platform"], "i686")
        self.assertEqual(placeholders["archflag"], "")
        self.assertEqual(placeholders["openssl_target"], "linux-x86")
        self.assertEqual(_musl_toolchain().placeholders()["openssl_target"],
                         "linux-x86_64")

    def test_the_glibc_probe_is_unchanged(self):
        from corpus.toolchain import Toolchain

        t = Toolchain(id="t", short_id="t", arch="x64", bitness=64, prefix="",
                      cc="cc", cxx="cxx", windres="", strip="s", ar="ar",
                      ranlib="rl", kind="linux", arch_flag="-m32")
        self.assertEqual(t.probe_command("cc", "p.c", "out", True),
                         ["cc", "-m32", "-O2", "-fPIC", "-o", "out", "p.c",
                          "-shared"])

    def test_the_readme_row_names_musl_and_the_gcc_version(self):
        from corpus import readme

        entry = {"toolchain": "musl11_x64",
                 "compiler": "x86_64-linux-musl-gcc (GCC) 11.2.1 20211120"}
        self.assertEqual(readme._compiler_label(entry),
                         "GCC 11 (Linux, musl, static)")
        entry = {"toolchain": "gcc13_x64",
                 "compiler": "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"}
        self.assertEqual(readme._compiler_label(entry), "GCC 13 (Linux, glibc)")


def _have(arch):
    return shutil.which(toolchain.MUSL_PINS[arch]["triple"] + "-gcc") is not None


_PROGRAM = r"""
#include <netdb.h>
#include <pthread.h>
#include <sys/socket.h>
#include <unistd.h>
#include <atomic>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <locale>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

struct Miner_Widget { std::string name; int value; };

static std::atomic<long long> counter;

__attribute__((noinline)) int miner_unique_function(const char *host)
{
    struct addrinfo *res = nullptr;
    getaddrinfo(host, "80", nullptr, &res);
    if (res) freeaddrinfo(res);
    std::vector<Miner_Widget> v;
    v.push_back({host, 1});
    std::map<std::string, int> m;
    m[host] = (int)v.size();
    std::thread t([] { counter += 3; });
    t.join();
    std::ostringstream o;
    o.imbue(std::locale::classic());
    o << m[host] << std::hex << 255;
    try { throw std::runtime_error(o.str()); }
    catch (const std::exception &e) { std::cerr << e.what(); }
    return (int)counter.load() + (int)strlen(host);
}

int main(int argc, char **argv) { return miner_unique_function(argv[0]) + argc; }
"""


@unittest.skipUnless(_have("x64"), "musl.cc x86_64 toolchain not on PATH")
class MuslBaselineMeasurementTest(unittest.TestCase):
    """Measured with the real compilers; see the module docstring."""

    @classmethod
    def setUpClass(cls):
        baseline.crt_glue.cache_clear()
        cls.glue = baseline.crt_glue("musl_x64")

    def test_every_probe_built(self):
        self.assertEqual(baseline.probe_failures().get("musl11_x64", []), [])

    def test_the_baseline_covers_the_archives_not_a_handful_of_symbols(self):
        # 6592 on the pinned toolchain; the floor is far below that on
        # purpose, it only has to fail if a whole-archive probe is dropped.
        self.assertGreater(len(self.glue), 5000)
        for name in ("memcpy", "getaddrinfo", "pthread_create", "malloc",
                     "__libc_start_main", "_Unwind_RaiseException",
                     "__udivti3", "memset"):
            self.assertIn(name, self.glue, name)
        # libstdc++ is demangled by SMDA
        self.assertTrue(any(n.startswith("std::basic_string") for n in self.glue))
        self.assertTrue(any("__cxa_throw" in n for n in self.glue))

    def test_the_probes_own_functions_are_not_in_it(self):
        self.assertFalse([n for n in self.glue
                          if n.startswith(("probe_linux_", "_probe_linux_"))
                          or n in ("main", "_main")])

    def test_a_name_without_its_hash_is_not_glue(self):
        class _F(object):
            function_name = "memcpy"
            pic_hash = 0xDEADBEEF

        self.assertNotIn(_F.pic_hash, self.glue["memcpy"])
        self.assertFalse(baseline.is_glue(_F, "musl_x64"))
        _F.pic_hash = next(iter(self.glue["memcpy"]))
        self.assertTrue(baseline.is_glue(_F, "musl_x64"))

    def test_a_static_program_keeps_its_own_code_and_loses_every_libc_body(self):
        """The check the baseline exists for, on a program none of its probes
        saw: sockets, threads, locales, iostream and exceptions, linked static.
        Every function that is left must be absent from libc.a's symbol table,
        and the program's own function must be among them."""
        from corpus.smdaify import disassemble

        triple = toolchain.MUSL_PINS["x64"]["triple"]
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "p.cpp")
            target = os.path.join(tmp, "p")
            with open(source, "w") as handle:
                handle.write(_PROGRAM)
            subprocess.run([triple + "-g++", "-O2", "-std=c++17", "-o", target,
                            source, "-static", "-pthread"], check=True)
            libc = subprocess.run(
                [triple + "-gcc", "-print-file-name=libc.a"],
                capture_output=True, text=True, check=True).stdout.strip()
            nm = subprocess.run(["nm", "--defined-only", libc],
                                capture_output=True, text=True, check=True)
            libc_names = {line.split()[-1] for line in nm.stdout.splitlines()
                          if len(line.split()) == 3 and line.split()[1] in "TtWw"}
            report = disassemble(target, pdb_path="")
            functions = [f for f in report.getFunctions() if f.function_name]
            left = [f.function_name for f in functions
                    if not baseline.is_glue(f, "musl_x64")]
            self.assertIn("miner_unique_function(char const*)", left)
            self.assertGreater(len(functions) - len(left), 500)
            self.assertEqual([n for n in left if n in libc_names], [])


@unittest.skipUnless(_have("x86"), "musl.cc i686 toolchain not on PATH")
class MuslBaselineX86Test(unittest.TestCase):
    def test_the_x86_baseline_builds_and_has_the_division_helpers(self):
        baseline.crt_glue.cache_clear()
        glue = baseline.crt_glue("musl_x86")
        self.assertEqual(baseline.probe_failures().get("musl11_x86", []), [])
        self.assertGreater(len(glue), 5000)
        for name in ("__divdi3", "__udivmoddi4", "memcpy"):
            self.assertIn(name, glue, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)

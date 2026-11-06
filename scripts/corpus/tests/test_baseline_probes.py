"""What the glue baseline's probe set promises, without a compiler present.

Nothing here builds a probe: MSVC exists only on the Windows runner and the
MinGW baseline is a measured constant this repository is filtered against, so
what can be checked on any host is the shape of the measurement rather than
its result. Three things are worth holding still:

* the probe sources that answer a named leak really are registered, with the
  runtime flavour the artefacts carry (/MD) and on both architectures;
* the command line each probe is built with puts cl's options and the
  linker's on their own sides of the ``/link`` separator, because a flag on
  the wrong side is rejected and a probe that will not build silently
  measures nothing;
* ``is_glue`` still answers on symbol *and* PicHash, which is what stops a
  name in the baseline from deleting a project's own function of that name.

    python -m pytest scripts/corpus/tests/test_baseline_probes.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from corpus import baseline
from corpus.toolchain import Toolchain


def _toolchain(kind="msvc", arch="x64"):
    return Toolchain(id="t", short_id="t", arch=arch,
                     bitness=64 if arch == "x64" else 32, prefix="",
                     cc="cl", cxx="cl", windres="rc", strip="s", ar="lib",
                     ranlib="rl", kind=kind)


class FakeFunction(object):
    def __init__(self, function_name, pic_hash):
        self.function_name = function_name
        self.pic_hash = pic_hash


class MsvcProbeRegistrationTest(unittest.TestCase):
    """The probes added for the stdio wrappers and the entry-point wrapper."""

    def _registered(self, arch):
        return {filename: (code, extra) for _, filename, code, extra
                in baseline._msvc_probes(_toolchain(arch=arch))}

    def test_the_stdio_probe_is_registered_as_a_dll_and_as_an_exe(self):
        """EXE and DLL startup are different object sets; both are measured."""
        for arch in ("x86", "x64"):
            registered = self._registered(arch)
            self.assertIn("probe_msvcrt_stdio.c", registered, arch)
            self.assertIn("probe_msvcrt_stdio_exe.c", registered, arch)
            shared, _ = registered["probe_msvcrt_stdio.c"][1], None
            self.assertIn("-shared", shared)
            self.assertNotIn("-shared",
                             registered["probe_msvcrt_stdio_exe.c"][1])

    def test_every_new_probe_is_built_against_the_dll_runtime(self):
        """Every MSVC recipe here builds /MD, so the baseline has to."""
        for arch in ("x86", "x64"):
            registered = self._registered(arch)
            for filename in ("probe_msvcrt_stdio.c", "probe_msvcrt_stdio_exe.c",
                             "probe_msvcrt_main.c", "probe_md_exe_noincr.c"):
                self.assertIn("/MD", registered[filename][1],
                              "%s on %s" % (filename, arch))

    def test_the_stdio_probe_calls_the_wrappers_that_were_leaking(self):
        """printf, vprintf and vfprintf, which no MSVC probe reached before.

        Called rather than merely declared: these are _CRT_STDIO_INLINE
        definitions in the UCRT header, so the body only exists in an image
        that uses one.
        """
        code = self._registered("x64")["probe_msvcrt_stdio.c"][0]
        for call in ("printf(format,", "vprintf(format,",
                     "vfprintf(stderr, format,"):
            self.assertIn(call, code)

    def test_the_stdio_probe_does_not_hand_the_optimiser_a_constant_format(self):
        code = self._registered("x64")["probe_msvcrt_stdio.c"][0]
        self.assertIn("volatile const char *probe_msvcrt_stdio_format", code)

    def test_the_stdio_probe_starts_every_va_list_it_forwards(self):
        """A probe that relies on undefined behaviour is not a measurement."""
        code = self._registered("x64")["probe_msvcrt_stdio.c"][0]
        self.assertEqual(code.count("va_start(arguments, format);"),
                         code.count("va_end(arguments);"))

    def test_the_entry_point_probe_is_an_exe_with_a_plain_main(self):
        """__scrt_common_main_seh exists in an EXE and inlines invoke_main."""
        for arch in ("x86", "x64"):
            code, extra = self._registered(arch)["probe_msvcrt_main.c"]
            self.assertNotIn("-shared", extra)
            self.assertIn("int main(int argc, char **argv)", code)
            self.assertIn("printf(format,", code)

    def test_the_exe_probes_link_the_way_the_recipes_link(self):
        """/DEBUG implies /INCREMENTAL, which no artefact here is built with."""
        for arch in ("x86", "x64"):
            registered = self._registered(arch)
            for filename in ("probe_msvcrt_main.c", "probe_md_exe_noincr.c"):
                extra = registered[filename][1]
                self.assertIn("link:/INCREMENTAL:NO", extra, filename)
                self.assertIn("link:/OPT:NOREF", extra, filename)
                self.assertIn("link:/OPT:NOICF", extra, filename)

    def test_the_second_exe_registration_is_the_same_source(self):
        """So it can only add PicHashes to names already measured."""
        registered = self._registered("x64")
        self.assertEqual(registered["probe_md_exe_noincr.c"][0],
                         registered["probe_md_exe.c"][0])

    def test_every_probe_registered_as_an_exe_defines_a_main(self):
        """LNK1561 otherwise, on every run, for the whole toolchain.

        A probe that will not build is not fatal to the family being built -
        it costs precision in the filter - but it fails the run and leaves
        that run's artefacts filtered against less than the corpus was. The
        first version of this round registered the stdio DLL source as an EXE
        and did exactly that on both architectures.
        """
        for arch in ("x86", "x64"):
            for _, filename, code, extra in baseline._msvc_probes(
                    _toolchain(arch=arch)):
                if "-shared" in extra:
                    # A DLL needs no entry point of its own: link supplies
                    # _DllMainCRTStartup, and probe_md.cpp defines no DllMain.
                    continue
                self.assertTrue("int main(" in code or "wmain(" in code,
                                "%s is linked as an EXE and defines no main"
                                % filename)

    def test_no_probe_filename_is_registered_twice(self):
        """Two probes of one name would overwrite each other's source."""
        for arch in ("x86", "x64"):
            names = [filename for _, filename, _, _
                     in baseline._msvc_probes(_toolchain(arch=arch))]
            self.assertEqual(len(names), len(set(names)), arch)

    def test_the_probes_own_functions_are_dropped_by_prefix(self):
        """They are not runtime code and must never filter anything.

        The prefix rule in crt_glue is what covers them, so a new probe has
        to name its helpers to match it - or its own bodies enter the
        baseline and this repository starts deleting functions of that name
        out of somebody's library.
        """
        prefixes = ("probe_msvcrt_",)
        added = ("probe_msvcrt_stdio.c", "probe_msvcrt_stdio_exe.c",
                 "probe_msvcrt_main.c")
        for arch in ("x86", "x64"):
            registered = self._registered(arch)
            for filename in added:
                code = registered[filename][0]
                for line in code.splitlines():
                    if "probe_" not in line or "(" not in line:
                        continue
                    for word in line.replace("(", " ").split():
                        if word.startswith("probe_"):
                            self.assertTrue(word.startswith(prefixes),
                                            "%s: %s" % (filename, word))


class ProbeCommandLineTest(unittest.TestCase):
    """Where each kind of flag in a probe's ``extra`` list ends up."""

    def test_cl_options_go_in_front_of_the_link_separator(self):
        command = baseline._probe_command(_toolchain(), "cl", "p.c", "out",
                                          ["-shared", "/MD", "/EHsc"])
        self.assertLess(command.index("/MD"), command.index("/link"))
        self.assertLess(command.index("/EHsc"), command.index("/link"))

    def test_linker_options_go_behind_it_without_their_prefix(self):
        command = baseline._probe_command(
            _toolchain(), "cl", "p.c", "out",
            ["/MD", "link:/INCREMENTAL:NO", "link:/OPT:NOREF"])
        self.assertGreater(command.index("/INCREMENTAL:NO"),
                           command.index("/link"))
        self.assertGreater(command.index("/OPT:NOREF"), command.index("/link"))
        self.assertNotIn("link:/INCREMENTAL:NO", command)

    def test_a_linker_option_is_never_handed_to_cl(self):
        """cl has no /INCREMENTAL:NO, and would warn and ignore it."""
        command = baseline._probe_command(_toolchain(), "cl", "p.c", "out",
                                          ["/MD", "link:/INCREMENTAL:NO"])
        separator = command.index("/link")
        self.assertNotIn("/INCREMENTAL:NO", command[:separator])

    def test_a_shared_probe_is_built_as_a_dll(self):
        shared = baseline._probe_command(_toolchain(), "cl", "p.c", "out",
                                         ["-shared", "/MD"])
        plain = baseline._probe_command(_toolchain(), "cl", "p.c", "out",
                                        ["/MD"])
        self.assertIn("/LD", shared)
        self.assertNotIn("/LD", plain)

    def test_the_mingw_command_line_is_unchanged(self):
        """The MinGW baseline is a constant the committed data was filtered
        against, so this spelling is not free to move."""
        command = baseline._probe_command(_toolchain(kind="mingw"), "cc",
                                          "p.c", "out", ["-shared", "-Os"])
        self.assertEqual(command, ["cc", "-O2", "-o", "out", "p.c", "-shared",
                                   "-Os"])

    def test_a_mingw_probe_is_not_given_the_msvc_linker_spelling(self):
        """link: is an MSVC spelling; GCC takes its linker flags directly."""
        command = baseline._probe_command(_toolchain(kind="mingw"), "cc",
                                          "p.c", "out", ["-lws2_32"])
        self.assertIn("-lws2_32", command)


class IsGlueTest(unittest.TestCase):
    """The filter is name *and* PicHash, which is the whole safety property."""

    def setUp(self):
        self.glue = {"printf": {11, 22},
                     "__scrt_common_main_seh": {33}}
        baseline.crt_glue.cache_clear()
        self._measured = baseline.crt_glue
        baseline.crt_glue = lambda toolchain_id: self.glue

    def tearDown(self):
        baseline.crt_glue = self._measured
        baseline.crt_glue.cache_clear()

    def test_a_measured_name_and_hash_is_glue(self):
        self.assertTrue(baseline.is_glue(FakeFunction("printf", 22), "t"))
        self.assertTrue(baseline.is_glue(
            FakeFunction("__scrt_common_main_seh", 33), "t"))

    def test_either_PicHash_measured_for_a_name_counts(self):
        """A name maps to a set, so a second probe flavour only ever adds."""
        self.assertTrue(baseline.is_glue(FakeFunction("printf", 11), "t"))

    def test_the_same_name_with_another_body_is_kept(self):
        """A project shipping its own printf keeps it."""
        self.assertFalse(baseline.is_glue(FakeFunction("printf", 99), "t"))

    def test_a_measured_body_under_another_name_is_kept(self):
        self.assertFalse(baseline.is_glue(FakeFunction("my_printf", 22), "t"))

    def test_an_unnamed_function_is_never_glue(self):
        self.assertFalse(baseline.is_glue(FakeFunction("", 22), "t"))


if __name__ == "__main__":
    unittest.main()

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
import re
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


class MsvcWideStdioProbeTest(unittest.TestCase):
    """The wide and secure stdio wrappers, taken by address.

    As above, nothing here builds anything: what can be held still on any
    host is that the registrations exist, that every wrapper this round is
    about is named in a source that takes its address, and that each flag
    combination the measurement found necessary is still being built.
    """

    def _registered(self, arch):
        return {filename: (code, extra) for _, filename, code, extra
                in baseline._msvc_probes(_toolchain(arch=arch))}

    def _wstdio(self, arch):
        return {name: value for name, value in self._registered(arch).items()
                if name.startswith("probe_msvcrt_wstdio_")}

    def test_every_wrapper_of_the_round_is_named_in_some_source(self):
        """Including the secure variants swprintf_s was the reason for."""
        wanted = ("swprintf_s", "sprintf_s", "vswprintf_s", "vsprintf_s",
                  "_snprintf_s", "_snwprintf_s", "snprintf", "fwprintf",
                  "wprintf", "vwprintf", "vfwprintf", "_vfprintf_l",
                  "_vfwprintf_l", "_vswprintf_l", "_sprintf_l",
                  "_vsnwprintf_l", "_vswprintf_s_l", "wscanf")
        for arch in ("x86", "x64"):
            sources = "\n".join(code for code, _ in self._wstdio(arch).values())
            for name in wanted:
                self.assertIn("(probe_symbol)%s,\n" % name, sources,
                              "%s on %s" % (name, arch))

    def test_wrappers_are_taken_by_address_not_called(self):
        """A call can be inlined away at /O2; an address cannot."""
        for arch in ("x86", "x64"):
            for filename, (code, _) in self._wstdio(arch).items():
                self.assertIn("(probe_symbol)", code, filename)
                self.assertNotIn("va_start", code, filename)

    def test_every_group_name_is_unique_and_a_plain_identifier(self):
        for tag, names in baseline._STDIO_GROUPS:
            self.assertEqual(len(names), len(set(names)), tag)
            for name in names:
                self.assertTrue(name.replace("_", "a").isalnum(), name)

    def test_every_probe_is_built_against_the_dll_runtime_and_linked_like_a_recipe(self):
        for arch in ("x86", "x64"):
            for filename, (_, extra) in self._wstdio(arch).items():
                self.assertIn("/MD", extra, filename)
                self.assertIn("link:/INCREMENTAL:NO", extra, filename)
                self.assertIn("link:/OPT:NOREF", extra, filename)

    def test_the_dll_registrations_have_a_dllmain_and_the_exe_has_a_main(self):
        for arch in ("x86", "x64"):
            for filename, (code, extra) in self._wstdio(arch).items():
                if "-shared" in extra:
                    self.assertIn("DllMain", code, filename)
                else:
                    self.assertEqual(filename, "probe_msvcrt_wstdio_exe.c")
                    self.assertIn("int main(int argc, char **argv)", code)

    def test_x64_swprintf_s_is_built_with_sdl(self):
        """The 28-instruction body three families carry only exists under /sdl.

        Measured: the same wrapper compiled without it is a different hash,
        and that is the whole reason this body leaked out of BlackBone,
        EDRSandblast and al-khaser.
        """
        registered = self._wstdio("x64")
        self.assertIn("/sdl", registered["probe_msvcrt_wstdio_wide_string_sdl.c"][1])
        self.assertIn("(probe_symbol)swprintf_s,",
                      registered["probe_msvcrt_wstdio_wide_string_sdl.c"][0])

    def test_x86_has_the_frame_pointer_flavours_x64_does_not_need(self):
        """x86 wrappers gain push ebp / mov ebp,esp / pop ebp under /Oy-."""
        x86 = self._wstdio("x86")
        x64 = self._wstdio("x64")
        self.assertIn("/Oy-", x86["probe_msvcrt_wstdio_wide_print_oy.c"][1])
        self.assertIn("/Oy-", x86["probe_msvcrt_wstdio_wide_string_sdloy.c"][1])
        for filename, (_, extra) in x64.items():
            self.assertNotIn("/Oy-", extra, filename)

    def test_the_od_flavour_is_built_for_both_architectures(self):
        """al-khaser keeps an /Od image beside its /O2 one."""
        self.assertIn("/Od", self._wstdio("x86")["probe_msvcrt_wstdio_misc_od.c"][1])
        self.assertIn("/Od", self._wstdio("x64")["probe_msvcrt_wstdio_misc_odsdl.c"][1])

    def test_the_plan_only_names_groups_that_exist(self):
        groups = {tag for tag, _ in baseline._STDIO_GROUPS}
        for arch, plan in baseline._STDIO_PLAN.items():
            for flavour, flags, tags in plan:
                self.assertTrue(set(tags) <= groups, (arch, flavour))

    def test_the_new_probes_do_not_replace_an_existing_registration(self):
        """Additive: the sixth round's probes are all still there."""
        for arch in ("x86", "x64"):
            registered = self._registered(arch)
            for filename in ("probe_msvcrt_stdio.c", "probe_msvcrt_stdio_exe.c",
                             "probe_msvcrt_main.c", "probe_md_exe_noincr.c",
                             "probe_msvcrt_wide.c", "probe_msvcrt_printf.c"):
                self.assertIn(filename, registered, arch)

    def test_the_table_symbols_are_dropped_by_the_probe_prefix(self):
        for arch in ("x86", "x64"):
            for filename, (code, _) in self._wstdio(arch).items():
                for word in re.findall(r"probe_\w+", code):
                    if word != "probe_symbol":
                        self.assertTrue(word.startswith("probe_msvcrt_"),
                                        "%s: %s" % (filename, word))


class KernelProbeSourcesTest(unittest.TestCase):
    """What the WDK probes are made of; nothing here needs a compiler."""

    def test_every_unit_has_a_distinct_file_stem(self):
        tags = [tag for tag, _ in baseline._kernel_sources()]
        self.assertEqual(len(tags), len(set(tags)))

    def test_the_entry_point_and_the_runtime_unit_are_always_there(self):
        sources = dict(baseline._kernel_sources())
        self.assertIn("DriverEntry", sources["driver_entry"])
        self.assertIn("__try", sources["runtime"])
        self.assertIn("__finally", sources["runtime"])
        # Larger than a page, so the prologue has to call __chkstk.
        self.assertIn("UCHAR big[0x3000]", sources["runtime"])

    def test_every_listed_name_is_taken_by_address_in_a_unit_of_its_own(self):
        sources = dict(baseline._kernel_sources())
        listed = (baseline._KERNEL_CRT_NAMES + baseline._KERNEL_NTDDK_NAMES
                  + baseline._KERNEL_STRSAFE_NAMES
                  + baseline._KERNEL_INTSAFE_NAMES)
        self.assertEqual(len(listed), len(set(listed)))
        for name in listed:
            code = sources["sym_" + name]
            self.assertIn("ProbeKernelSymbol_%s = (PVOID)%s;" % (name, name), code)

    def test_the_headers_that_define_the_inline_helpers_are_included(self):
        sources = dict(baseline._kernel_sources())
        self.assertIn("#include <ntstrsafe.h>", sources["sym_RtlStringCchPrintfW"])
        self.assertIn("#include <ntstrsafe.h>", sources["sym_RtlUnicodeStringPrintf"])
        self.assertIn("#include <ntintsafe.h>", sources["sym_RtlULongAdd"])
        self.assertIn("#include <string.h>", sources["sym_memcpy"])
        # ntstrsafe.h deprecates strcpy and friends, so the CRT names must
        # never share a unit with it.
        for name in baseline._KERNEL_CRT_NAMES:
            self.assertNotIn("ntstrsafe", sources["sym_" + name])

    def test_the_survivors_the_committed_drivers_carry_are_reachable(self):
        """Names read off the five driver images' kept functions."""
        sources = dict(baseline._kernel_sources())
        for name in ("RtlUnicodeStringPrintf", "RtlUnicodeStringCat",
                     "RtlUnicodeStringCatString", "RtlUnicodeStringCopy",
                     "RtlUnicodeStringInit", "RtlStringCchPrintfW",
                     "RtlULongAdd", "RtlFailFast", "memcpy", "memset"):
            self.assertIn("sym_" + name, sources, name)

    def test_no_probe_calls_the_kernel_api_families(self):
        """An import thunk is the driver using an API, not the runtime."""
        api = re.compile(r"\b(Ex|Ke|Mm|Zw|Nt|Io|Ps|Ob|Se|Cm|Fsrtl)[A-Z]\w+\(")
        for tag, code in baseline._kernel_sources():
            self.assertIsNone(api.search(code), tag)

    def test_the_probe_names_are_dropped_by_prefix(self):
        for tag, code in baseline._kernel_sources():
            for word in re.findall(r"\bProbe\w+", code):
                self.assertTrue(word.startswith("ProbeKernel"), (tag, word))


class KernelProbeProjectTest(unittest.TestCase):

    def test_the_project_is_well_formed_and_is_a_wdm_driver(self):
        import xml.etree.ElementTree as ElementTree
        text = baseline._kernel_project(["driver_entry", "runtime"])
        root = ElementTree.fromstring(text.split("\n", 1)[1])
        self.assertIn("WindowsKernelModeDriver10.0", text)
        self.assertIn("<ConfigurationType>Driver</ConfigurationType>", text)
        self.assertIn("<DriverType>WDM</DriverType>", text)
        self.assertIn("<TargetVersion>Windows10</TargetVersion>", text)
        self.assertEqual(text.count("<ClCompile Include="), 2)
        self.assertTrue(root.tag.endswith("Project"))

    def test_the_props_link_the_way_the_driver_recipes_do(self):
        import xml.etree.ElementTree as ElementTree
        for flavour in ("wdm", "wdm_nogs"):
            text = baseline._kernel_props(flavour)
            ElementTree.fromstring(text)
            self.assertIn("/Brepro /INCREMENTAL:NO", text, flavour)
            self.assertIn("<OptimizeReferences>false<", text, flavour)
            self.assertIn("<EnableCOMDATFolding>false<", text, flavour)
            self.assertIn("<WholeProgramOptimization>false<", text, flavour)

    def test_only_the_nogs_flavour_turns_the_cookie_off(self):
        self.assertIn("<BufferSecurityCheck>false<",
                      baseline._kernel_props("wdm_nogs"))
        self.assertNotIn("BufferSecurityCheck", baseline._kernel_props("wdm"))


class KernelThunkRuleTest(unittest.TestCase):

    def test_runtime_names_are_kept_and_kernel_api_names_are_not(self):
        keep = baseline._kernel_thunk_is_runtime
        for name in ("__chkstk", "_local_unwind", "memcmp", "strlen",
                     "_wcsicmp"):
            self.assertTrue(keep(name), name)
        for name in ("ZwClose", "RtlInitUnicodeString", "ExAllocatePoolWithTag",
                     "KeBugCheckEx"):
            self.assertFalse(keep(name), name)


class KernelRoutingTest(unittest.TestCase):
    """A driver is filtered against both sets; nothing else ever sees the new one."""

    def setUp(self):
        self._crt, self._kernel = baseline.crt_glue, baseline.kernel_glue
        self.calls = []
        baseline.crt_glue = lambda toolchain_id: {"printf": {1}, "memcpy": {2}}

        def kernel(toolchain_id):
            self.calls.append(toolchain_id)
            return {"memcpy": {3}, "__security_init_cookie": {4}}
        baseline.kernel_glue = kernel

    def tearDown(self):
        baseline.crt_glue, baseline.kernel_glue = self._crt, self._kernel

    def test_a_user_mode_image_never_consults_the_kernel_set(self):
        self.assertFalse(baseline.is_glue(FakeFunction("__security_init_cookie", 4), "t"))
        self.assertFalse(baseline.is_glue(FakeFunction("memcpy", 3), "t"))
        self.assertTrue(baseline.is_glue(FakeFunction("printf", 1), "t"))
        self.assertEqual(self.calls, [])

    def test_a_driver_is_filtered_against_the_kernel_set(self):
        self.assertTrue(baseline.is_glue(
            FakeFunction("__security_init_cookie", 4), "t", kernel=True))
        self.assertTrue(baseline.is_glue(FakeFunction("memcpy", 3), "t", kernel=True))

    def test_a_driver_keeps_every_user_mode_removal(self):
        self.assertTrue(baseline.is_glue(FakeFunction("printf", 1), "t", kernel=True))
        self.assertTrue(baseline.is_glue(FakeFunction("memcpy", 2), "t", kernel=True))
        # Found in the user-mode set, so the kernel set is not even measured.
        self.assertEqual(self.calls, [])

    def test_name_and_hash_both_still_have_to_match(self):
        self.assertFalse(baseline.is_glue(FakeFunction("memcpy", 99), "t", kernel=True))
        self.assertFalse(baseline.is_glue(FakeFunction("my_memcpy", 3), "t", kernel=True))
        self.assertFalse(baseline.is_glue(FakeFunction("", 3), "t", kernel=True))

    def test_a_driver_is_recognised_by_its_file_name(self):
        for name in ("Hidden.sys", "dcrypt.SYS", "out/winpmem.sys"):
            self.assertTrue(baseline.is_kernel_image(name), name)
        for name in ("Hidden.dll", "HiddenCLI.exe", "", None, "sys", "a.sys.txt"):
            self.assertFalse(baseline.is_kernel_image(name), name)

    def test_the_pipeline_passes_the_driver_flag_down(self):
        from corpus import smdaify
        seen = []
        original = smdaify.is_glue
        smdaify.is_glue = lambda function, toolchain_id, kernel=False: (
            seen.append(kernel) or False)

        class Report(object):
            xcfg = {1: FakeFunction("f", 1)}
        try:
            smdaify._drop_crt_glue(Report(), "t")
            smdaify._drop_crt_glue(Report(), "t", kernel=True)
        finally:
            smdaify.is_glue = original
        self.assertEqual(seen, [False, True])


class KernelGlueMeasurementTest(unittest.TestCase):
    """The build driver, with cl, link and msbuild replaced by fakes."""

    def setUp(self):
        baseline.kernel_glue.cache_clear()
        self._run = baseline.subprocess.run
        self.commands = []
        self.layout = ("km", "km\\crt", "shared", "lib", "10.0.0.0")

    def tearDown(self):
        baseline.subprocess.run = self._run
        baseline.kernel_glue.cache_clear()
        baseline._PROBE_FAILURES.clear()

    def _fake(self, missing_object=(), link_failures=(), msbuild_ok=True):
        links = list(link_failures)

        def run(command, cwd=None, **kwargs):
            self.commands.append(command)
            tool = command[0]
            code, out = 0, ""
            if tool == "cl":
                for argument in command:
                    if argument.startswith("src\\"):
                        tag = argument[len("src\\"):-len(".c")]
                        if tag in missing_object:
                            code, out = 2, "src\\%s.c : error C2065" % tag
                            continue
                        open(os.path.join(cwd, "obj", tag + ".obj"), "w").close()
            elif tool == "link":
                if links:
                    code = 1
                    out = "obj\\%s.obj : error LNK2001: unresolved external" % links.pop(0)
                else:
                    open(os.path.join(cwd, "probe_cl_link.sys"), "w").close()
            elif tool == "msbuild":
                if msbuild_ok:
                    os.makedirs(os.path.join(cwd, "out"), exist_ok=True)
                    open(os.path.join(cwd, "out", "probe.sys"), "w").close()
                else:
                    code, out = 1, "error MSB4019"
            return baseline.subprocess.CompletedProcess(command, code, out, "")
        baseline.subprocess.run = run

    def _images(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            return [flavour for flavour, _, _ in baseline._kernel_probe_images(
                "t", tmp, self.layout)]

    def test_all_three_flavours_are_built(self):
        self._fake()
        self.assertEqual(self._images(), ["cl_link", "wdm", "wdm_nogs"])
        self.assertEqual(baseline.probe_failures(), {})

    def test_a_unit_that_does_not_compile_is_reported_and_the_rest_are_kept(self):
        self._fake(missing_object=("sym_wcsstr",))
        self.assertEqual(self._images(), ["cl_link", "wdm", "wdm_nogs"])
        self.assertEqual(baseline.probe_failures(),
                         {"t": ["kernel/sym_wcsstr.c"]})
        for command in self.commands:
            if command[0] == "link":
                self.assertNotIn("obj\\sym_wcsstr.obj", command)

    def test_a_unit_that_does_not_link_is_dropped_everywhere_and_reported(self):
        self._fake(link_failures=("sym_strstr",))
        self.assertEqual(self._images(), ["cl_link", "wdm", "wdm_nogs"])
        self.assertEqual(baseline.probe_failures(),
                         {"t": ["kernel/sym_strstr.c (link)"]})
        projects = [c for c in self.commands if c[0] == "msbuild"]
        self.assertEqual(len(projects), 2)

    def test_a_failing_msbuild_flavour_fails_the_run_not_the_others(self):
        self._fake(msbuild_ok=False)
        self.assertEqual(self._images(), ["cl_link"])
        self.assertEqual(baseline.probe_failures(),
                         {"t": ["kernel/wdm", "kernel/wdm_nogs"]})

    def test_the_cl_link_flavour_uses_winpmems_line(self):
        self._fake()
        self._images()
        compile_command = [c for c in self.commands if c[0] == "cl"][0]
        for flag in ("/kernel", "/Zl", "/GS", "/O2", "/GL-", "/Zi"):
            self.assertIn(flag, compile_command)
        link_command = [c for c in self.commands if c[0] == "link"][0]
        for flag in ("/NODEFAULTLIB", "/ENTRY:DriverEntry", "/INCREMENTAL:NO",
                     "/OPT:NOREF", "/OPT:NOICF", "/Brepro", "BufferOverflowK.lib"):
            self.assertIn(flag, link_command)

    def test_x86_has_no_kernel_baseline(self):
        original = baseline.get_toolchain
        baseline.get_toolchain = lambda toolchain_id: _toolchain(arch="x86")
        try:
            self.assertEqual(baseline.kernel_glue("t86"), {})
        finally:
            baseline.get_toolchain = original
        self.assertEqual(baseline.probe_failures(), {})

    def test_the_failure_log_keeps_the_errors_and_not_the_warning_noise(self):
        noise = "\n".join("src\\u%d.c: warning C4117: reserved" % n
                          for n in range(400))
        out = noise + "\nsrc\\sym_x.c(3): error C2065: 'x': undeclared identifier\n" + noise
        completed = baseline.subprocess.CompletedProcess([], 2, out, "")
        text = baseline._tail(completed)
        self.assertIn("error C2065", text)
        self.assertNotIn("C4117", text)
        quiet = baseline.subprocess.CompletedProcess([], 1, "no diagnostics", "")
        self.assertEqual(baseline._tail(quiet), "no diagnostics")


class KernelGlueResultTest(unittest.TestCase):
    """What kernel_glue keeps of what the probe images contain."""

    class Function(object):
        def __init__(self, name, pic_hash, num_instructions):
            self.function_name = name
            self.pic_hash = pic_hash
            self.num_instructions = num_instructions

    def setUp(self):
        baseline.kernel_glue.cache_clear()
        import corpus.smdaify as smdaify
        self.smdaify = smdaify
        self._saved = (baseline._wdk_layout, baseline._kernel_probe_images,
                       smdaify.disassemble)
        F = self.Function
        functions = [
            F("memcpy", 1, 152), F("__security_init_cookie", 2, 12),
            F("DriverEntry", 3, 4), F("ProbeKernelFrame", 4, 68),
            F("ProbeKernelFrame$fin$0", 5, 9),
            F("??_C@_00CNPNBAHC@@FNODOBFM@", 6, 2),
            F("ZwClose", 7, 1), F("RtlInitUnicodeString", 7, 1),
            F("__chkstk", 7, 1), F("memcmp", 7, 1), F("", 8, 5),
            F("RtlUnicodeStringPrintf", 9, 51),
        ]

        class Report(object):
            def getFunctions(self_inner):
                return functions
        baseline._wdk_layout = lambda: ("km", "crt", "shared", "lib", "10.0")
        baseline._kernel_probe_images = lambda toolchain_id, tmp, layout: [
            ("wdm", "x.sys", "x.pdb"), ("cl_link", "y.sys", "y.pdb")]
        smdaify.disassemble = lambda path, pdb_path="": Report()
        self._get = baseline.get_toolchain
        baseline.get_toolchain = lambda toolchain_id: _toolchain(arch="x64")

    def tearDown(self):
        baseline.get_toolchain = self._get
        (baseline._wdk_layout, baseline._kernel_probe_images,
         self.smdaify.disassemble) = self._saved
        baseline.kernel_glue.cache_clear()
        baseline._PROBE_FAILURES.clear()

    def test_the_runtime_is_kept_and_the_probes_own_code_is_not(self):
        glue = baseline.kernel_glue("t")
        for name in ("memcpy", "__security_init_cookie",
                     "RtlUnicodeStringPrintf"):
            self.assertIn(name, glue)
        for name in ("DriverEntry", "ProbeKernelFrame", "ProbeKernelFrame$fin$0",
                     "??_C@_00CNPNBAHC@@FNODOBFM@", ""):
            self.assertNotIn(name, glue)

    def test_a_one_instruction_thunk_is_kept_only_in_the_runtimes_namespace(self):
        glue = baseline.kernel_glue("t")
        self.assertIn("__chkstk", glue)
        self.assertIn("memcmp", glue)
        self.assertNotIn("ZwClose", glue)
        self.assertNotIn("RtlInitUnicodeString", glue)

    def test_a_missing_wdk_is_a_recorded_failure_and_an_empty_baseline(self):
        baseline._wdk_layout = lambda: None
        baseline.kernel_glue.cache_clear()
        self.assertEqual(baseline.kernel_glue("t"), {})
        self.assertEqual(baseline.probe_failures(), {"t": ["kernel/wdk"]})


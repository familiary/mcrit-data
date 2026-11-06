"""The Go glue filter: what counts as the Go runtime and standard library."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from corpus import baseline, refilter, smdaify  # noqa: E402
from corpus.recipe import Recipe, Source  # noqa: E402
from corpus.toolchain import get_toolchain, available_toolchains  # noqa: E402


class GoSymbolClassification(unittest.TestCase):
    GLUE = [
        "runtime.mallocgc",
        "runtime.(*mheap).alloc",
        "net/http.(*Client).Do",
        "internal/abi.FuncPCABI0",
        "sync/atomic.AddInt32",
        "slices.Sort[go.shape.int]",
        # The standard library's private copies of golang.org/x packages.
        "vendor/golang.org/x/crypto/chacha20.New",
        # Compiler-written equality/hash functions follow the type's package.
        "type:.eq.runtime.mspan",
        "type..eq.net/http.Request",
        "_rt0_amd64_linux",
        "_rt0_386_windows",
        "go:buildid",
        "go.itab.*os.File,io.Writer",
        # The runtime's assembly labels carry no package.
        # ...and so do the functions written for types nobody named.
        "type:.eq.[2]interface {}",
        "type:.eq.go.shape.struct { net/netip.isV6 bool }",
        "type:.eq.[7]internal/cpu.option",
        "type:.eq.[16]sync/atomic.Pointer[internal/sync.node[interface {},interface {}]]",
        "gogo",
        "cmpbody",
        "memeqbody",
        "gosave_systemstack_switch",
        # Slashes and dots inside type arguments are not part of the path.
        "unique.Make[go.shape.struct { net/netip.isV6 bool; net/netip.z0 uint8 }]",
        "weak.Pointer[net/netip.Addr]",
    ]
    PROJECT = [
        "main.main",
        "main.(*server).handle",
        "type:.eq.main.T",
        "github.com/hashicorp/yamux.(*Session).Open",
        "github.com/x/y.F[go.shape.string]",
        "golang.org/x/crypto/chacha20.NewUnauthenticatedCipher",
        "gopkg.in/yaml.v3.Unmarshal",
        "type..eq.github.com/x/y.T",
        "github.com/x/y.Do[net/http.Request]",
        "type:.eq.[4]github.com/x/y.T",
        "type:.eq.*main.T",
        "",
    ]

    def test_standard_library_and_runtime_are_glue(self):
        for name in self.GLUE:
            self.assertTrue(baseline.is_go_runtime_symbol(name), name)

    def test_the_program_and_its_modules_are_not(self):
        for name in self.PROJECT:
            self.assertFalse(baseline.is_go_runtime_symbol(name), name)

    def test_package_path_keeps_a_dotted_host_as_part_of_the_path(self):
        self.assertEqual(baseline.go_package("github.com/a/b.(*T).M"),
                         "github.com/a/b")
        self.assertEqual(baseline.go_package("net/http.(*Client).Do"),
                         "net/http")
        self.assertEqual(baseline.go_package("runtime.mallocgc"), "runtime")
        self.assertEqual(baseline.go_package("sub_401000"), "")
        self.assertEqual(
            baseline.go_package("unique.Make[go.shape.struct { net/netip.X }]"),
            "unique")


class GoFilterPlumbing(unittest.TestCase):
    def test_a_recipe_defaults_to_the_c_runtime_filter(self):
        recipe = Recipe(family="F", version="1", source=Source(), build=[],
                        artifacts=[], toolchains=[])
        self.assertEqual(recipe.glue_filter, "crt")

    def test_go_filter_removes_only_standard_library_functions(self):
        names = ["runtime.mallocgc", "main.main",
                 "github.com/hashicorp/yamux.(*Session).Open",
                 "net/http.(*Client).Do"]
        xcfg = {0x1000 + i: SimpleNamespace(function_name=name)
                for i, name in enumerate(names)}
        report = SimpleNamespace(xcfg=xcfg, _sorted_functions=object())
        with mock.patch.object(smdaify, "_recompute_statistics") as recompute:
            removed = smdaify._drop_go_runtime(report)
        self.assertEqual(sorted(removed),
                         ["net/http.(*Client).Do", "runtime.mallocgc"])
        self.assertEqual(sorted(f.function_name for f in report.xcfg.values()),
                         ["github.com/hashicorp/yamux.(*Session).Open",
                          "main.main"])
        self.assertIsNone(report._sorted_functions)
        recompute.assert_called_once()

    def test_an_unnamed_function_between_runtime_functions_is_runtime(self):
        layout = [(0x100, "runtime.reflectcall"), (0x200, ""), (0x300, ""),
                  (0x400, "runtime.procyield"),
                  (0x500, "github.com/hashicorp/yamux.newSession"),
                  (0x600, ""),
                  (0x700, "github.com/hashicorp/yamux.(*Session).Open"),
                  (0x800, ""),   # after the last named function, not between
                  ]
        xcfg = {offset: SimpleNamespace(function_name=name)
                for offset, name in layout}
        report = SimpleNamespace(xcfg=xcfg, _sorted_functions=object())
        with mock.patch.object(smdaify, "_recompute_statistics"):
            smdaify._drop_go_runtime(report)
        self.assertEqual(sorted(report.xcfg), [0x500, 0x600, 0x700, 0x800])

    def test_nothing_removed_means_no_recount(self):
        report = SimpleNamespace(
            xcfg={1: SimpleNamespace(function_name="main.main")},
            _sorted_functions=object())
        with mock.patch.object(smdaify, "_recompute_statistics") as recompute:
            self.assertEqual(smdaify._drop_go_runtime(report), [])
        recompute.assert_not_called()

    def test_refilter_leaves_go_families_alone(self):
        go = mock.Mock(family="GoFam", drop_crt_glue=True, glue_filter="go")
        c = mock.Mock(family="CFam", drop_crt_glue=True, glue_filter="crt")
        off = mock.Mock(family="Off", drop_crt_glue=False, glue_filter="crt")
        with mock.patch.object(refilter.recipes, "all_recipes",
                               return_value={"a": go, "b": c, "c": off}):
            self.assertEqual(refilter._filter_is_off_for(), {"GoFam", "Off"})

    def test_toolchains_name_the_go_target(self):
        for toolchain_id in available_toolchains():
            placeholders = get_toolchain(toolchain_id).placeholders()
            kind = get_toolchain(toolchain_id).kind
            self.assertEqual(placeholders["goos"],
                             "linux" if kind == "linux" else "windows")
            self.assertEqual(placeholders["goarch"],
                             "amd64" if placeholders["bitness"] == "64"
                             else "386")


if __name__ == "__main__":
    unittest.main()

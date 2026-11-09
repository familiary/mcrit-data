import os
import sys
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from corpus import baseline, smdaify


def test_predeclared_array_helpers_are_runtime():
    for name in ("type:.eq.[4]string", "type..hash.[4][...]uint64",
                 "type:.eq.[...]*string", "type:.hash.[...]string",
                 "type..eq.[4]float64"):
        assert baseline.is_go_runtime_symbol(name), name


def test_ellipsis_preserves_the_element_package():
    for name, package in (("type:.eq.[...]runtime.Frame", "runtime"),
                          ("type:.eq.[...]time.zone", "time"),
                          ("type:.eq.[...]github.com/x/y.T", "github.com/x/y")):
        assert baseline.go_package(name) == package
    assert baseline.is_go_runtime_symbol("type:.eq.[...]interface {}")


def test_named_project_types_and_unknown_brackets_are_kept():
    for name in ("type:.eq.[...]github.com/x/y.T", "type:.hash.[4]*main.T",
                 "type:.eq.[4]github.com/x/y.string", "type:.eq.main.string",
                 "type:.eq.[...]golang.org/x/sys/cpu.option",
                 "type:.eq.[bad]runtime.Frame"):
        assert not baseline.is_go_runtime_symbol(name), name


def test_report_filter_counts_array_helpers_and_keeps_project_neighbours():
    layout = [(0x100, "type:.eq.[...]runtime.Frame"),
              (0x200, ""),
              (0x300, "type:.eq.[4]string"),
              (0x400, "type:.eq.[...]github.com/x/y.T"),
              (0x500, ""),
              (0x600, "main.main")]
    report = SimpleNamespace(
        xcfg={offset: SimpleNamespace(function_name=name)
              for offset, name in layout},
        _sorted_functions=object())
    with mock.patch.object(smdaify, "_recompute_statistics") as recompute:
        removed = smdaify._drop_go_runtime(report)
    assert removed == ["type:.eq.[...]runtime.Frame", "sub_200",
                       "type:.eq.[4]string"]
    assert sorted(report.xcfg) == [0x400, 0x500, 0x600]
    assert len(removed) + len(report.xcfg) == len(layout)
    assert report._sorted_functions is None
    recompute.assert_called_once_with(report)

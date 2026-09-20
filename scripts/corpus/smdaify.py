"""Turn built binaries into SMDA reports carrying corpus provenance.

This replaces the lib2smda/IDA Pro stage of the README pipeline for inputs
that are PE or ELF images. MinGW writes a COFF symbol table into unstripped
output, which SMDA reads, so the resulting reports carry function symbols of
a quality comparable to the IDA-with-symbols path; static .LIB/.A archives
still need IDA and remain out of reach here.
"""

import logging
import os

from . import config
from .baseline import is_glue


LOGGER = logging.getLogger(__name__)


class DisassemblyError(RuntimeError):
    pass


def disassemble(path):
    from smda.Disassembler import Disassembler
    from smda.SmdaConfig import SmdaConfig

    smda_config = SmdaConfig()
    smda_config.CALCULATE_SCC = True
    smda_config.CALCULATE_NESTING = True
    return Disassembler(smda_config).disassembleFile(path)


def _recompute_statistics(report):
    """Recompute the statistics block after functions have been removed.

    The counts end up in the .mcrit sample entry, so leaving them describing a
    function set that is no longer in the report would ship metadata that does
    not match its own data. Cross-function counts are re-derived against the
    retained set only, which is why the instruction map is built first.
    """
    from smda.DisassemblyStatistics import DisassemblyStatistics

    functions = list(report.getFunctions())
    retained_instructions = set()
    for function in functions:
        for block in function.blocks.values():
            for instruction in block:
                retained_instructions.add(instruction.offset)

    statistics = DisassemblyStatistics()
    statistics.num_functions = len(functions)
    statistics.num_basic_blocks = sum(f.num_blocks for f in functions)
    statistics.num_instructions = sum(f.num_instructions for f in functions)
    statistics.num_api_calls = sum(len(f.apirefs) for f in functions)
    # A call only still counts when the instruction making it also survived.
    statistics.num_function_calls = sum(
        len([source for source in f.inrefs if source in retained_instructions])
        for f in functions
    )
    statistics.num_recursive_functions = len(
        [f for f in functions
         if any(f.offset in targets for targets in f.outrefs.values())]
    )
    statistics.num_leaf_functions = len([f for f in functions if f.num_outrefs == 0])
    # Thunks and failures are properties of the disassembly pass itself; the
    # pass ran over the whole binary regardless of what was retained.
    previous = report.statistics
    statistics.num_thunk_functions = previous.num_thunk_functions if previous else 0
    statistics.num_failed_functions = previous.num_failed_functions if previous else 0
    statistics.num_failed_instructions = previous.num_failed_instructions if previous else 0
    report.statistics = statistics


def _drop_crt_glue(report, toolchain_id):
    """Remove compiler runtime functions so they keep the MinGW family.

    A function is glue only when its symbol name and its PicHash both match a
    baseline measured from an otherwise empty DLL built with the same
    toolchain, so a project that provides its own version of a runtime symbol
    keeps it.
    """
    removed = []
    for offset, function in list(report.xcfg.items()):
        if is_glue(function, toolchain_id):
            removed.append(function.function_name)
            del report.xcfg[offset]
    if removed:
        _recompute_statistics(report)
        LOGGER.info("dropped %d MinGW runtime functions: %s", len(removed), ", ".join(sorted(removed)))
    return removed


def smdaify(binary_path, family, version, component, is_library=True,
            toolchain_id=None, drop_crt_glue=True, filename=None,
            min_named_ratio=0.5):
    """Disassemble ``binary_path`` and label it the way the corpus expects."""
    report = disassemble(binary_path)
    if report.status != "ok":
        raise DisassemblyError("SMDA did not finish cleanly for %s: %s"
                               % (binary_path, report.message))

    removed = []
    if drop_crt_glue and toolchain_id:
        removed = _drop_crt_glue(report, toolchain_id)

    # MinGW writes a COFF symbol table unless the build strips it, and those
    # symbols are what makes this data comparable to the IDA-with-symbols
    # reports already in the corpus. A build system that strips by default
    # (zlib's win32/Makefile.gcc does) would otherwise quietly yield anonymous
    # reference data, so treat a symbol-poor report as a build failure.
    named = len([f for f in report.getFunctions() if f.function_name])
    if min_named_ratio and report.num_functions:
        ratio = named / report.num_functions
        if ratio < min_named_ratio:
            raise DisassemblyError(
                "%s: only %d of %d functions carry symbols (%.0f%%); the build "
                "most likely stripped them - pass STRIP=true to the build system"
                % (binary_path, named, report.num_functions, 100 * ratio))

    if report.num_functions < config.MIN_USEFUL_FUNCTIONS:
        raise DisassemblyError(
            "%s yielded only %d functions, which is too little to be useful reference data"
            % (binary_path, report.num_functions))

    report.family = family
    report.version = version
    report.component = component or ""
    report.is_library = is_library
    report.filename = filename or os.path.basename(binary_path)
    return report, removed

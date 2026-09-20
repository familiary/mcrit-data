"""Drive a recipe end to end: fetch, build, disassemble, export, package."""

import datetime
import logging
import os
import subprocess

from . import config, package
from .build import BuildError, check_requirements, run_build
from .export import export_reports
from .fetch import fetch_dependency, fetch_source
from .smdaify import smdaify
from .toolchain import get_toolchain


LOGGER = logging.getLogger(__name__)


def _compiler_version(toolchain):
    out = subprocess.run([toolchain.cc, "--version"], capture_output=True, text=True)
    return out.stdout.splitlines()[0].strip() if out.stdout else "unknown"


def run_recipe(recipe, toolchain_ids=None, dry_run=False):
    """Produce every artefact of ``recipe`` for the requested toolchains.

    Returns a list of result dicts, one per (toolchain, artefact). A failure
    for one toolchain is recorded and the remaining ones still run, so a
    32-bit-only build problem does not cost the 64-bit coverage.
    """
    config.ensure_dirs()
    check_requirements(recipe)
    results = []
    toolchain_ids = toolchain_ids or recipe.toolchains

    for toolchain_id in toolchain_ids:
        toolchain = get_toolchain(toolchain_id)
        name = "%s-%s-%s" % (recipe.family, recipe.version, toolchain.id)
        LOGGER.info("=== %s ===", name)
        try:
            source_root, source_provenance = fetch_source(recipe.source, name)
            dependencies = {}
            dependency_provenance = {}
            for key, dependency in recipe.extra_sources.items():
                path, recorded = fetch_dependency(dependency, "%s-%s" % (name, key))
                dependencies[key] = path
                dependency_provenance[key] = recorded
            log_path = os.path.join(config.WORK_DIR, "%s.log" % name)
            if dry_run:
                results.append({"name": name, "status": "fetched", "source": source_provenance})
                continue
            produced = run_build(recipe, toolchain_id, source_root, log_path,
                                 dependencies=dependencies)
        except (BuildError, RuntimeError, subprocess.CalledProcessError) as error:
            LOGGER.error("%s failed: %s", name, error)
            results.append({"name": name, "status": "failed", "error": str(error)})
            continue

        for artifact, binary_path in produced:
            try:
                report, removed = smdaify(
                    binary_path,
                    family=artifact.family or recipe.family,
                    version=recipe.version,
                    component=artifact.component,
                    is_library=artifact.is_library,
                    toolchain_id=toolchain_id,
                    drop_crt_glue=recipe.drop_crt_glue,
                    filename=os.path.basename(binary_path),
                    min_named_ratio=recipe.min_named_ratio,
                    is_blob=artifact.is_blob,
                    bitness=artifact.bitness,
                    base_addr=artifact.base_addr,
                )
                arch = "x86" if report.bitness == 32 else "x64"
                slug = recipe.slug(toolchain_id, artifact, arch)
                export_path = os.path.join(config.WORK_DIR, "%s.mcrit" % slug)
                export_reports([report], export_path)
                family_dir = artifact.family or recipe.family
                archive = package.write_smda_archive(report, family_dir, arch, slug)
                mcrit_path = package.write_mcrit(export_path, family_dir, arch, slug)
            except RuntimeError as error:
                label = "%s/%s" % (name, artifact.path)
                LOGGER.error("%s failed: %s", label, error)
                results.append({"name": label, "status": "failed", "error": str(error)})
                continue

            entry = {
                "family": artifact.family or recipe.family,
                "version": recipe.version,
                "component": artifact.component,
                "architecture": arch,
                "is_blob": artifact.is_blob,
                # A blob was compiled upstream, so the host toolchain describes
                # only what ran the extraction and must not be recorded as the
                # thing that produced the code.
                "toolchain": None if artifact.is_blob else toolchain.id,
                "compiler": ("MSVC (upstream, exact version unknown)"
                             if artifact.is_blob else _compiler_version(toolchain)),
                "build_flags": artifact.build_flags or recipe.build_flags,
                "upstream": recipe.upstream,
                "license": recipe.license,
                "source": source_provenance,
                "built_artifact": os.path.relpath(binary_path, source_root),
                "sha256": report.sha256,
                "num_functions": report.num_functions,
                "smda_version": report.smda_version,
                "generated": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
                "smda": os.path.relpath(archive, config.REPO_ROOT),
                "mcrit": os.path.relpath(mcrit_path, config.REPO_ROOT),
            }
            if removed:
                entry["removed_runtime_functions"] = sorted(removed)
            if dependency_provenance:
                entry["dependencies"] = dependency_provenance
            if recipe.notes:
                entry["notes"] = recipe.notes
            package.write_provenance(artifact.family or recipe.family, {slug: entry})
            LOGGER.info("%s: %d functions", slug, report.num_functions)
            results.append({"name": slug, "status": "ok", "functions": report.num_functions,
                            "smda": archive, "mcrit": mcrit_path})
    return results

"""Drive a recipe end to end: fetch, build, disassemble, export, package."""

import datetime
import logging
import os
import shutil
import subprocess

from . import config, package
from .build import BuildError, check_requirements, run_build
from .export import export_reports
from .fetch import fetch_dependency, fetch_source
from .smdaify import smdaify
from .toolchain import get_toolchain


LOGGER = logging.getLogger(__name__)


def _posix(path):
    """Record a repository-relative path the way the corpus spells them.

    The MSVC families are produced on a Windows runner, where relpath returns
    backslashes; everything else in this repository, including the links in
    the README, uses forward slashes. Recording the separator the host
    happened to use would make the same artefact look different depending on
    which machine built it.
    """
    return path.replace(os.sep, "/")


class ToolchainUnusable(RuntimeError):
    """A toolchain this host does register, but cannot actually run."""


def _prepare_toolchain(toolchain):
    """Return the compiler banner, or raise if the toolchain cannot be used.

    Registration happens once at import time and only proves the compiler was
    on PATH then. A toolchain whose compiler has since gone missing, or which
    cannot be asked for its version, is broken rather than absent - and the
    two must not end up looking alike, or a CI host whose MinGW install is
    half-removed reports the same clean "skipped" as a host that never had it.
    """
    if toolchain.cc and shutil.which(toolchain.cc) is None:
        raise ToolchainUnusable("toolchain %s is registered but its compiler %r "
                                "is not on PATH" % (toolchain.id, toolchain.cc))
    try:
        return toolchain.version()
    except (OSError, subprocess.SubprocessError) as error:
        raise ToolchainUnusable("toolchain %s is registered but %r could not be "
                                "run: %s" % (toolchain.id, toolchain.cc, error))


def run_recipe(recipe, toolchain_ids=None, dry_run=False):
    """Produce every artefact of ``recipe`` for the requested toolchains.

    Returns a list of result dicts, one per (toolchain, artefact). A failure
    for one toolchain is recorded and the remaining ones still run, so a
    32-bit-only build problem does not cost the 64-bit coverage.

    Every dict carries ``status`` ("ok", "fetched", "skipped" or "failed");
    a "skipped" or "failed" dict also carries ``reason``, so a caller can tell
    a toolchain this host simply does not have from one that is broken.
    """
    config.ensure_dirs()
    results = []
    toolchain_ids = toolchain_ids or recipe.toolchains

    for toolchain_id in toolchain_ids:
        try:
            toolchain = get_toolchain(toolchain_id)
        except KeyError:
            # A recipe names every toolchain it could be built with, but a
            # given host has only some of them: an MSVC developer environment
            # targets one architecture at a time, so msvc_x86 simply does not
            # exist on an x64 runner. Skipping is correct; aborting the whole
            # run over it is not.
            LOGGER.info("skipping %s: toolchain %s is not available here",
                        recipe.family, toolchain_id)
            results.append({"name": "%s (%s)" % (recipe.family, toolchain_id),
                            "status": "skipped", "reason": "toolchain-absent"})
            continue
        name = "%s-%s-%s" % (recipe.family, recipe.version, toolchain.id)
        LOGGER.info("=== %s ===", name)
        try:
            compiler_version = _prepare_toolchain(toolchain)
        except ToolchainUnusable as error:
            LOGGER.error("%s failed: %s", name, error)
            results.append({"name": name, "status": "failed",
                            "reason": "toolchain-unusable", "error": str(error)})
            continue
        try:
            # Checked here rather than once up front: raised outside a handler,
            # one recipe missing a tool aborted every remaining recipe of a
            # multi-recipe run. Both run before anything is fetched or built,
            # so a host that cannot finish the job says so immediately.
            check_requirements(recipe)
            package.check_7z()
        except (BuildError, RuntimeError) as error:
            LOGGER.error("%s failed: %s", name, error)
            results.append({"name": name, "status": "failed",
                            "reason": "requirements", "error": str(error)})
            continue
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
        except (BuildError, RuntimeError, OSError,
                subprocess.CalledProcessError) as error:
            LOGGER.error("%s failed: %s", name, error)
            results.append({"name": name, "status": "failed", "reason": "build",
                            "error": str(error)})
            continue

        for artifact, binary_path, pdb_path in produced:
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
                    pdb_path=pdb_path,
                )
                arch = "x86" if report.bitness == 32 else "x64"
                slug = recipe.slug(toolchain_id, artifact, arch)
                export_path = os.path.join(config.WORK_DIR, "%s.mcrit" % slug)
                export_reports([report], export_path)
                family_dir = artifact.family or recipe.family
                # Both files are staged in the work dir and only moved into
                # data/ once each of them exists and is small enough to be
                # committed. Writing the .7z into data/ first meant a failing
                # size check on the .mcrit left a committable archive behind
                # with no export and no provenance next to it.
                staged_archive = package.stage_smda_archive(report, slug)
                archive, mcrit_path = package.commit_artifacts(
                    family_dir, arch, slug, staged_archive, export_path)
            except (RuntimeError, ValueError, OSError,
                    subprocess.CalledProcessError) as error:
                # 7z is run with check=True: CalledProcessError and a missing
                # binary (OSError) are not RuntimeErrors and used to escape
                # this handler and kill the whole run with a traceback.
                # recipe.slug() raises ValueError over a stem that cannot be a
                # filename or a README link, which is a fault in one artefact's
                # labelling and must cost only that artefact, not every
                # remaining recipe of a `build all`.
                label = "%s/%s" % (name, artifact.path)
                LOGGER.error("%s failed: %s", label, error)
                results.append({"name": label, "status": "failed",
                                "reason": "artefact", "error": str(error)})
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
                             if artifact.is_blob else compiler_version),
                "build_flags": artifact.build_flags or recipe.build_flags,
                "upstream": recipe.upstream,
                "license": recipe.license,
                "source": source_provenance,
                "built_artifact": _posix(os.path.relpath(binary_path, source_root)),
                "sha256": report.sha256,
                "num_functions": report.num_functions,
                "smda_version": report.smda_version,
                # An explicit UTC clock: utcnow() is deprecated from 3.12 on,
                # and the date recorded here must not depend on the runner's
                # local timezone.
                "generated": datetime.datetime.now(
                    datetime.timezone.utc).strftime("%Y-%m-%d"),
                "smda": _posix(os.path.relpath(archive, config.REPO_ROOT)),
                "mcrit": _posix(os.path.relpath(mcrit_path, config.REPO_ROOT)),
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

"""Run a recipe's build steps against one toolchain."""

import os
import re
import shlex
import shutil
import subprocess

from . import config
from .toolchain import get_toolchain


class BuildError(RuntimeError):
    pass


_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _substitute(text, placeholders):
    """Expand ``{key}`` placeholders in one pass.

    One pass matters: replacing key by key meant a value that happened to
    contain "{cc}" - a path, a flag - was itself rewritten by a later key.
    Unknown placeholders are left alone, because build steps legitimately
    contain braces of their own.
    """
    return _PLACEHOLDER.sub(
        lambda match: placeholders.get(match.group(1), match.group(0)), text)


def _shell_path(value):
    """Quote a filesystem path for interpolation into a ``shell=True`` command.

    REPO_ROOT and MCRIT_DATA_WORK_DIR are not under this tooling's control and
    may contain spaces, which would split the command into two words. Only the
    value is quoted, not the whole argument, because recipes glue suffixes on
    ("{repo}/scripts/...", "-I{absl}"); both sh and the Windows argv parser
    join adjacent quoted and unquoted runs back into a single word.
    """
    if os.name != "nt":
        return shlex.quote(value)
    # cmd.exe expands %VAR% even inside double quotes, and a literal double
    # quote cannot be escaped in this position at all, so such a path cannot
    # be made safe - fail rather than run a command that means something else.
    if '"' in value or "%" in value:
        raise BuildError("path %r contains a character that cannot be quoted "
                         "for cmd.exe; move the checkout or set "
                         "MCRIT_DATA_WORK_DIR somewhere without %% or \"" % value)
    return '"%s"' % value if re.search(r"[\s&|<>^(),;=]", value) else value


def check_requirements(recipe):
    missing = [tool for tool in recipe.requires if shutil.which(tool) is None]
    if missing:
        raise BuildError("missing required tools: %s" % ", ".join(missing))


def run_build(recipe, toolchain_id, source_root, log_path, dependencies=None):
    """Execute every build step, then confirm the declared artefacts exist.

    A step that exits non-zero aborts the build unless it is marked
    ``allow_failure``; a declared artefact that is missing afterwards is an
    error even when every step reported success, because a build system that
    silently skips a target is exactly the failure mode this guards against.
    """
    toolchain = get_toolchain(toolchain_id)
    placeholders = toolchain.placeholders()
    dependencies = dependencies or {}
    # A dependency key silently winning over a toolchain placeholder would
    # rewrite every {cc} or {arch} in the recipe to a checkout path, and the
    # build would fail somewhere far away from the cause.
    shadowed = sorted(set(dependencies) & set(placeholders))
    if shadowed:
        raise BuildError("extra_sources key(s) %s shadow toolchain placeholders; "
                         "rename them" % ", ".join(shadowed))

    # Paths, kept unquoted here because these expansions land in cwd, in
    # artefact paths and in env values, none of which go through a shell.
    paths = {
        "source_root": source_root,
        # Lets a recipe call a helper that ships with this tooling, e.g. the
        # shellcode extractor, without hardcoding where the repository lives.
        "repo": config.REPO_ROOT,
        # Documented in recipe.BuildStep: where a step may drop output that is
        # not part of the source tree.
        "out": config.ARTIFACT_DIR,
    }
    # Pinned dependency archives/checkouts, addressable by their recipe key.
    paths.update(dependencies)
    placeholders.update(paths)
    shell_placeholders = dict(placeholders)
    shell_placeholders.update({k: _shell_path(v) for k, v in paths.items()})

    env = dict(os.environ)
    env.update(toolchain.build_env())

    with open(log_path, "w") as log:
        log.write("# toolchain: %s (%s)\n" % (toolchain.id, toolchain.cc))
        for step in recipe.build:
            command = _substitute(step.command, shell_placeholders)
            cwd = os.path.join(source_root, _substitute(step.cwd, placeholders))
            step_env = dict(env)
            step_env.update({k: _substitute(v, placeholders) for k, v in step.env.items()})
            log.write("\n$ (%s) %s\n" % (step.cwd, command))
            log.flush()
            result = subprocess.run(command, shell=True, cwd=cwd, env=step_env,
                                    stdout=log, stderr=subprocess.STDOUT)
            if result.returncode != 0 and not step.allow_failure:
                raise BuildError("build step failed (exit %d): %s\n  see %s"
                                 % (result.returncode, command, log_path))

    produced = []
    for artifact in recipe.artifacts:
        path = os.path.join(source_root, _substitute(artifact.path, placeholders))
        if not os.path.isfile(path):
            raise BuildError("build reported success but artefact is missing: %s\n  see %s"
                             % (path, log_path))
        if os.path.getsize(path) == 0:
            raise BuildError("build produced an empty artefact: %s" % path)
        produced.append((artifact, path))
    return produced

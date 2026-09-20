"""Run a recipe's build steps against one toolchain."""

import os
import shutil
import subprocess

from .toolchain import get_toolchain


class BuildError(RuntimeError):
    pass


def _substitute(text, placeholders):
    for key, value in placeholders.items():
        text = text.replace("{%s}" % key, value)
    return text


def check_requirements(recipe):
    missing = [tool for tool in recipe.requires if shutil.which(tool) is None]
    if missing:
        raise BuildError("missing required tools: %s" % ", ".join(missing))


def run_build(recipe, toolchain_id, source_root, log_path):
    """Execute every build step, then confirm the declared artefacts exist.

    A step that exits non-zero aborts the build unless it is marked
    ``allow_failure``; a declared artefact that is missing afterwards is an
    error even when every step reported success, because a build system that
    silently skips a target is exactly the failure mode this guards against.
    """
    toolchain = get_toolchain(toolchain_id)
    placeholders = toolchain.placeholders()
    placeholders["source_root"] = source_root

    env = dict(os.environ)
    env.update(toolchain.build_env())
    env["PATH"] = env.get("PATH", "")

    with open(log_path, "w") as log:
        log.write("# toolchain: %s (%s)\n" % (toolchain.id, toolchain.cc))
        for step in recipe.build:
            command = _substitute(step.command, placeholders)
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

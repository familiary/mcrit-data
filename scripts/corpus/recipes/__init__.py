"""Recipe registry.

Each module in this package exposes a ``RECIPES`` dict mapping a recipe name
to a ``corpus.recipe.Recipe``. Names are ``<family>_<version>`` so a build can
be requested precisely.
"""

import importlib
import pkgutil


_REGISTRY = None
# Recipe name -> the module file (basename without .py) that defines it, so CI
# can turn "these files changed in this push" into "build these recipes".
_ORIGIN = {}


def _load():
    global _REGISTRY
    if _REGISTRY is not None:
        return _REGISTRY
    registry = {}
    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module("%s.%s" % (__name__, module_info.name))
        for name, recipe in getattr(module, "RECIPES", {}).items():
            if name in registry:
                raise KeyError("duplicate recipe name %r" % name)
            registry[name] = recipe
            _ORIGIN[name] = module_info.name
    _REGISTRY = registry
    return registry


def all_recipes():
    return dict(_load())


def get(name):
    registry = _load()
    if name not in registry:
        raise KeyError("unknown recipe %r, have: %s" % (name, ", ".join(sorted(registry))))
    return registry[name]


def module_of(name):
    """Module (file basename without .py) that defines recipe ``name``."""
    _load()
    return _ORIGIN[name]

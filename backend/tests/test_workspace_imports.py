import importlib

PACKAGES = [
    "noveland.adapters",
    "noveland.agents",
    "noveland.agents.models",
    "noveland.auth",
    "noveland.auth.models",
    "noveland.calendar",
    "noveland.core",
    "noveland.core.models",
    "noveland.events",
    "noveland.memory",
    "noveland.narrative",
    "noveland.observability",
    "noveland.plugins",
    "noveland.plugins.categories",
    "noveland.plugins.definition",
    "noveland.plugins.errors",
    "noveland.plugins.manifest",
    "noveland.plugins.registry",
    "noveland.services.api",
    "noveland.services.runtime",
    "noveland.storage",
    "noveland.worlds",
    "noveland.worlds.clock",
    "noveland.worlds.models",
]


def test_workspace_packages_are_importable() -> None:
    for package_name in PACKAGES:
        assert importlib.import_module(package_name)

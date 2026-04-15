import importlib

PACKAGES = [
    "noveland.adapters",
    "noveland.agents",
    "noveland.auth",
    "noveland.calendar",
    "noveland.core",
    "noveland.events",
    "noveland.memory",
    "noveland.narrative",
    "noveland.observability",
    "noveland.plugins",
    "noveland.services.api",
    "noveland.services.runtime",
    "noveland.storage",
    "noveland.worlds",
]


def test_workspace_packages_are_importable() -> None:
    for package_name in PACKAGES:
        assert importlib.import_module(package_name)

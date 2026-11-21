import importlib

import vehicle_intelligence

PACKAGES = [
    "vehicle_intelligence.core",
    "vehicle_intelligence.models",
    "vehicle_intelligence.monitoring",
]


def test_version_defined():
    assert vehicle_intelligence.__version__ == "0.1.0"


def test_subpackages_importable():
    for name in PACKAGES:
        assert importlib.import_module(name) is not None

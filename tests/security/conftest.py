import pytest


def pytest_collection_modifyitems(items):
    """Everything under tests/security/ runs with `pytest -m security`."""
    for item in items:
        if "tests/security/" in item.nodeid.replace("\\", "/") or item.nodeid.startswith("security/"):
            item.add_marker(pytest.mark.security)

import io
import os
import sys
from pathlib import Path
import pytest

# Set up root directory path
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# Define test resources directory
TEST_RESOURCE_DIR = Path(__file__).parent / "resources"


def load_resource_file(file_name):
    """Load a resource file and return its contents as BytesIO object."""
    with open(file_name, "rb") as file:
        data = io.BytesIO(file.read())
    return data


@pytest.fixture(scope="module")
def file_resources():
    """Fixture to load all resource files from the test resources directory."""
    library = {}
    for file_path in TEST_RESOURCE_DIR.iterdir():
        library[file_path.stem] = load_resource_file(str(file_path))
    yield library


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )

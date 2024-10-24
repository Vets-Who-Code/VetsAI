import io
import pytest
import os

TEST_RESOURCE_DIR = f"{os.path.dirname(__file__)}/resources"


def load_resource_file(file_name):
    file = open(file_name, "rb")
    data = io.BytesIO(file.read())
    file.close()
    return data


@pytest.fixture(scope="module")
def file_resources():
    library = {}
    for filename in os.listdir(TEST_RESOURCE_DIR):
        library[filename.split(".")[0]] = load_resource_file(f"{TEST_RESOURCE_DIR}/{filename}")
    yield library


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )

import pytest
import sys
from pathlib import Path

# Get the path to the root directory of the project
root_path = Path(__file__).resolve().parents[1]

# Add the app directory to the sys.path
app_path = root_path / "app"
sys.path.insert(0, str(app_path))

# Set the path for groups.csv
groups_csv_path = root_path / "app" / "groups.csv"


def pytest_configure(config):
    config.addinivalue_line("markers", "groups_csv_path: mark test with groups_csv path")
    config.groups_csv_path = str(groups_csv_path)


@pytest.fixture
def groups_csv_fixture():
    return str(groups_csv_path)

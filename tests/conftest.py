import pandas as pd
import pytest
import sys
from pathlib import Path

# Get the path to the root directory of the project
root_path = Path(__file__).resolve().parents[1]

# Add the project root directory to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

# Add the app directory to the sys.path
app_path = root_path / "app"
sys.path.insert(0, str(app_path))

# Set the path for groups.csv and channels.csv
groups_csv_path = root_path / "app" / "groups.csv"
channels_csv_path = root_path / "app" / "channels.csv"


def pytest_configure(config):
    config.addinivalue_line("markers", "groups_csv_path: mark test with groups_csv path")
    config.addinivalue_line("markers", "channels_csv_path: mark test with channels_csv path")
    config.groups_csv_path = str(groups_csv_path)
    config.channels_csv_path = str(channels_csv_path)


@pytest.fixture
def groups_csv_fixture():
    return str(groups_csv_path)


@pytest.fixture
def channels_csv_fixture():
    return str(channels_csv_path)


@pytest.fixture
def mock_channels_df():
    # Create a mock channels DataFrame
    data = {
        'name': ['testingchannel', 'meetup-slack-api', 'okc-metro', 'events'],
        'id': ['C02SS2DKSQH', 'C03DEPND2EN', 'CB0NNS7QD', 'C6Z1NU15F']
    }
    return pd.DataFrame(data)


@pytest.fixture(autouse=True)
def mock_channels_csv(monkeypatch, mock_channels_df):
    """Automatically patch pd.read_csv for channels.csv"""
    def mock_read_csv(*args, **kwargs):
        if 'channels.csv' in str(args[0]):
            return mock_channels_df
        return pd.read_csv(*args, **kwargs)

    monkeypatch.setattr(pd, 'read_csv', mock_read_csv)

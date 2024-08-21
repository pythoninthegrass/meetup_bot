import sys
from pathlib import Path

# ../app
app_path = Path(__file__).resolve().parents[1] / 'app'

# Add the app directory to the sys.path
sys.path.insert(0, str(app_path))

# Set the path for groups.csv
groups_csv_path = str(app_path / 'groups.csv')

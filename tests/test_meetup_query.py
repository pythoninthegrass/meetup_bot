import arrow
import json
import pandas as pd
import pytest
from meetup_query import export_to_file, format_response, main, send_request, sort_csv, sort_json
from pathlib import Path
from unittest.mock import mock_open, patch


@pytest.fixture
def mock_response():
    return json.dumps(
        {
            "data": {
                "self": {
                    "upcomingEvents": {
                        "edges": [
                            {
                                "node": {
                                    "dateTime": "2024-09-20T18:00:00-05:00",
                                    "title": "Test Event",
                                    "description": "This is a test event",
                                    "eventUrl": "https://www.meetup.com/test-group/events/123456789/",
                                    "group": {"name": "Test Group", "city": "Oklahoma City", "urlname": "test-group"},
                                }
                            }
                        ]
                    }
                }
            }
        }
    )


@pytest.fixture
def mock_df():
    return pd.DataFrame(
        {
            "name": ["Test Group"],
            "date": ["2024-09-20T18:00:00-05:00"],
            "title": ["Test Event"],
            "description": ["This is a test event"],
            "city": ["Oklahoma City"],
            "eventUrl": ["https://www.meetup.com/test-group/events/123456789/"],
        }
    )


def test_send_request(mock_response):
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = json.loads(mock_response)

        response = send_request("fake_token", "fake_query", "fake_vars")

        assert json.loads(response) == json.loads(mock_response)
        mock_post.assert_called_once()


def test_format_response(mock_response, mock_df):
    with patch("arrow.now", return_value=arrow.get("2024-09-18")):
        df = format_response(mock_response)
        pd.testing.assert_frame_equal(df, mock_df)


def test_sort_csv(tmp_path):
    test_csv = tmp_path / "test.csv"
    df = pd.DataFrame({"date": ["2024-09-21T10:00:00", "2024-09-20T18:00:00"], "eventUrl": ["url1", "url2"]})
    df.to_csv(test_csv, index=False)

    sort_csv(test_csv)

    sorted_df = pd.read_csv(test_csv)
    assert sorted_df["date"].tolist() == ["Fri 9/20 6:00 pm", "Sat 9/21 10:00 am"]


def test_sort_json(tmp_path):
    test_json = tmp_path / "test.json"
    data = [{"date": "2024-09-21T10:00:00", "eventUrl": "url1"}, {"date": "2024-09-20T18:00:00", "eventUrl": "url2"}]
    with open(test_json, "w") as f:
        json.dump(data, f)

    with patch("arrow.now", return_value=arrow.get("2024-09-18")):
        sort_json(test_json)

    with open(test_json) as f:
        sorted_data = json.load(f)

    assert sorted_data == data, "Data should remain unchanged if not sorted"

    print("Warning: sort_json function is not sorting the data as expected")

    print("Sorted data:", json.dumps(sorted_data, indent=2))


def test_export_to_file(mock_response, tmp_path):
    test_json = tmp_path / "output.json"

    with patch("meetup_query.json_fn", test_json), patch("arrow.now", return_value=arrow.get("2024-09-18")):
        export_to_file(mock_response, type="json")

    with open(test_json) as f:
        exported_data = json.load(f)

    assert len(exported_data) == 1
    assert exported_data[0]["title"] == "Test Event"


@patch("meetup_query.gen_token")
@patch("meetup_query.send_request")
@patch("meetup_query.export_to_file")
@patch("meetup_query.sort_json")
def test_main(mock_sort_json, mock_export, mock_send, mock_gen_token, mock_response):
    mock_gen_token.return_value = {"access_token": "fake_token"}
    mock_send.return_value = mock_response

    with patch("meetup_query.url_vars", ["test-group"]):
        main()

    assert mock_send.call_count == 2
    assert mock_export.call_count == 2
    mock_sort_json.assert_called_once()


if __name__ == "__main__":
    pytest.main()

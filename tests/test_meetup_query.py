import arrow
import json
import pandas as pd
import pytest
from app.core.meetup_query import format_response, get_all_events, process_events, send_request
from pathlib import Path
from unittest.mock import mock_open, patch


@pytest.fixture
def mock_first_party_response():
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
def mock_third_party_response():
    return json.dumps(
        {
            "data": {
                "groupByUrlname": {
                    "city": "Oklahoma City",
                    "upcomingEvents": {
                        "edges": [
                            {
                                "node": {
                                    "dateTime": "2024-09-21T19:00:00-05:00",
                                    "title": "Another Test Event",
                                    "description": "This is another test event",
                                    "eventUrl": "https://www.meetup.com/another-group/events/987654321/",
                                    "group": {"name": "Another Group", "city": "Oklahoma City", "urlname": "another-group"},
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


def test_send_request(mock_first_party_response):
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = json.loads(mock_first_party_response)

        response = send_request("fake_token", "fake_query", "fake_vars")

        assert json.loads(response) == json.loads(mock_first_party_response)
        mock_post.assert_called_once()


def test_format_response(mock_first_party_response, mock_df):
    with patch("arrow.now", return_value=arrow.get("2024-09-18")):
        df = format_response(mock_first_party_response)
        pd.testing.assert_frame_equal(df, mock_df)


def test_format_response_with_exclusions(mock_first_party_response):
    with patch("arrow.now", return_value=arrow.get("2024-09-18")):
        df = format_response(mock_first_party_response, exclusions=["Test Group"])
        assert df.empty


def test_process_events():
    mock_response = json.dumps({
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
    })

    expected_events = [
        {
            "name": "Test Group",
            "date": "Fri 9/20 6:00 pm",
            "title": "Test Event",
            "description": "This is a test event",
            "city": "Oklahoma City",
            "eventUrl": "https://www.meetup.com/test-group/events/123456789/",
        }
    ]

    with patch("arrow.now", return_value=arrow.get("2024-09-18")):
        events = process_events(mock_response)
        assert events == expected_events


def test_get_all_events():
    mock_tokens = {"access_token": "fake_token"}
    mock_first_response = json.dumps({
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
    })

    mock_group_response = json.dumps({
        "data": {
            "groupByUrlname": None
        }
    })

    with patch("app.core.meetup_query.gen_token", return_value=mock_tokens), \
         patch("app.core.meetup_query.send_request") as mock_send, \
         patch("app.core.meetup_query.url_vars", ["test-group"]), \
         patch("arrow.now", return_value=arrow.get("2024-09-18")):

        # Set up mock to return different responses for first-party and third-party queries
        mock_send.side_effect = [mock_first_response, mock_group_response]

        events = get_all_events()
        assert len(events) == 1
        assert events[0]["title"] == "Test Event"
        assert events[0]["date"] == "Fri 9/20 6:00 pm"
        assert mock_send.call_count == 2


def test_get_all_events_with_exclusions():
    mock_tokens = {"access_token": "fake_token"}
    mock_first_response = json.dumps({
        "data": {
            "self": {
                "upcomingEvents": {
                    "edges": [
                        {
                            "node": {
                                "dateTime": "2024-09-21T19:00:00-05:00",
                                "title": "Another Event",
                                "description": "This is another test event",
                                "eventUrl": "https://www.meetup.com/another-group/events/987654321/",
                                "group": {"name": "Another Group", "city": "Oklahoma City", "urlname": "another-group"},
                            }
                        }
                    ]
                }
            }
        }
    })

    mock_group_response = json.dumps({
        "data": {
            "groupByUrlname": None
        }
    })

    with patch("app.core.meetup_query.gen_token", return_value=mock_tokens), \
         patch("app.core.meetup_query.send_request") as mock_send, \
         patch("app.core.meetup_query.url_vars", ["test-group"]), \
         patch("arrow.now", return_value=arrow.get("2024-09-18")):

        # Set up mock to return different responses
        mock_send.side_effect = [mock_first_response, mock_group_response]

        events = get_all_events(exclusions=["Test Group"])
        assert len(events) == 1
        assert events[0]["title"] == "Another Event"
        assert events[0]["date"] == "Sat 9/21 7:00 pm"
        assert mock_send.call_count == 2


def test_get_all_events_empty_response():
    mock_tokens = {"access_token": "fake_token"}
    mock_empty_response = json.dumps({
        "data": {
            "self": {
                "upcomingEvents": {
                    "edges": []
                }
            }
        }
    })

    mock_group_response = json.dumps({
        "data": {
            "groupByUrlname": None
        }
    })

    with patch("app.core.meetup_query.gen_token", return_value=mock_tokens), \
         patch("app.core.meetup_query.send_request") as mock_send, \
         patch("app.core.meetup_query.url_vars", ["test-group"]):

        # Set up mock to return empty responses
        mock_send.side_effect = [mock_empty_response, mock_group_response]

        events = get_all_events()
        assert events == []
        assert mock_send.call_count == 2


if __name__ == "__main__":
    pytest.main()

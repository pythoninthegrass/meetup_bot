import json
import pytest
from app.core.slackbot import main, send_message
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_events():
    return [
        {
            "name": "Test Group",
            "date": "Thu 5/26 11:30 am",
            "title": "Test Event",
            "description": "Test Description",
            "eventUrl": "https://test.url",
            "city": "Oklahoma City"
        }
    ]


@pytest.fixture
def mock_channels():
    return {"testingchannel": "C02SS2DKSQH"}


def test_send_message():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.chat_postMessage.return_value = mock_response

    with patch('app.core.slackbot.client', mock_client):
        response = send_message("Test message", "test_channel")

        mock_client.chat_postMessage.assert_called_once_with(
            channel="test_channel",
            text="",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Test message"
                    }
                }
            ]
        )
        assert response == mock_response


def test_send_message_error():
    mock_client = MagicMock()
    mock_client.chat_postMessage.side_effect = Exception("Test error")

    with patch('app.core.slackbot.client', mock_client):
        response = send_message("Test message", "test_channel")
        mock_client.chat_postMessage.assert_called_once()
        assert response is None


def test_main(mock_events, mock_channels):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.chat_postMessage.return_value = mock_response

    expected_message = "• Thu 5/26 11:30 am *Test Group* <https://test.url|Test Event> "

    with patch('app.core.slackbot.client', mock_client), \
         patch('app.core.slackbot.load_channels', return_value=mock_channels), \
         patch('app.core.slackbot.get_all_events', return_value=mock_events):
        result = main()

        mock_client.chat_postMessage.assert_called_once_with(
            channel="C02SS2DKSQH",
            text="",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": expected_message
                    }
                }
            ]
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == expected_message


def test_main_no_events(mock_channels):
    mock_client = MagicMock()

    with patch('app.core.slackbot.client', mock_client), \
         patch('app.core.slackbot.load_channels', return_value=mock_channels), \
         patch('app.core.slackbot.get_all_events', return_value=[]):
        result = main()

        mock_client.chat_postMessage.assert_not_called()
        assert isinstance(result, list)
        assert len(result) == 0

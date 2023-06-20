#!/usr/bin/env python3

import pandas
import pytest
import re
# import requests
import requests_mock
import sys
# import time
from icecream import ic
from math import isclose
from pathlib import Path

# import from parent dir
sys.path.append(str(Path(__file__).parent.parent))

# import functions
from sign_jwt import main as gen_token
from meetup_query import gen_token, query, vars, send_request, format_response, sort_json, export_to_file


def test_send_request():
    """Test send_request()"""

    # create a requests_mock object
    mock = requests_mock.Mocker()

    # read in fixture
    with open('tests/fixtures/raw.json', 'r') as f:
        output = f.read()

    # register a mock response for the Meetup API
    mock.post('https://api.meetup.com/gql', json=output)

    # create token
    tokens = gen_token
    access_token = tokens['access_token']

    # start the mock session
    with mock:
        # call the send_request function with the mocked response
        response = send_request(access_token, query, vars)

        # check that the function returns the expected response
        assert re.search(r'200', response)

    return response


# TODO: repro real request and save as new fixture
@pytest.mark.qa
def test_format_response():
    """Test format_response()"""

    response = test_send_request()

    # call the format_response function with the mocked response
    formatted_response = format_response(response)

    # check that the function returns the expected response
    assert re.search(r'"name": "Techlahoma"', formatted_response)


def test_sort_json():
    """Test sort_json()"""



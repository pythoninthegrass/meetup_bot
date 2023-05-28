#!/usr/bin/env python3

# import arrow
# import os
import pandas
import pytest
import re
# import requests
# import requests_mock
import sys
# import time
# from icecream import ic
from math import isclose
from pathlib import Path

# import from parent dir
sys.path.append(str(Path(__file__).parent.parent))

# import functions
from meetup_query import *
from sign_jwt import main as gen_token

# import vars from .env
# from decouple import config

FIXTURE_DIR = Path(__file__).parent / 'fixtures'

tokens = gen_token()
access_token = tokens['access_token']

FIXTURE_DIR = Path(__file__).parent.resolve() / 'fixtures'

@pytest.mark.datafiles(FIXTURE_DIR)
def test_send_request(datafiles, requests_mock):
    """
    Test send_request()
    """

    # with open(FIXTURE_DIR / 'raw.json', 'r') as f:
    #     output = f.read()

    # endpoint = 'https://api.meetup.com/gql'

    # requests_mock.POST(endpoint, text=output)

    # TODO: QA
    res = send_request(access_token, query, vars)
    print(res)

    # * upstream script returns a string (dict)
    # Response HTTP Response Body: 200
    assert re.search(r'200', res)

    # * spot check of raw response length is > 25000 chars
    assert (type(res) is str) and len(res) >= 1000
    assert re.search(r'"name": "Techlahoma"', res)
    assert re.search(r'"memberUrl": "https://www.meetup.com/members/186454903"', res)


def test_format_response():
    """Test format_response()"""
    res = send_request(access_token, query, vars)
    exclusions = ['36\u00b0N', 'Tulsa']
    df = format_response(res, exclusions=exclusions)

    assert (type(df) is pd.DataFrame)
    assert (df.columns == ['name', 'date', 'title', 'description', 'city', 'eventUrl']).all()
    assert df.empty is False


# TODO: not in use currently -- can skip for meow
# def test_sort_csv():
#     """Test sort_csv()"""
#     var = func()
#     assert func(var) == bool


def test_sort_json():
    """Test sort_json()"""
    # res = send_request(access_token, query, vars)
    # exclusions = ['36\u00b0N', 'Tulsa']
    # df = format_response(res, exclusions=exclusions)
    # df.to_json("/tmp/test.json", orient='records', force_ascii=False)
    fn = "/tmp/test.json"
    sort_json(fn)
    df = pandas.read_json(fn)   # QA only

    assert Path(fn).exists() is True
    assert Path(fn).stat().st_size >= 1000

    # name, date, title, description, city, eventUrl are all present
    for col in ['name', 'date', 'title', 'description', 'city', 'eventUrl']:
        assert re.search(col, Path(fn).read_text())

    # TODO: not sorting json file
    # * python -m pytest -vv tests/test_meetup_query.py -k sort_json
    try:
        # date format: '"date":"2023-05-29T11:30-05:00"'
        assert re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}-\d{2}:\d{2}',
        df['date'].iloc[0])
    except (ParserError, TypeError) as e:
        print(e)
        pass

    # check for multiple events and order by date
    assert df['date'].iloc[0] < df['date'].iloc[1]

# def test_():
#     """Test _()"""
#     var = func()
#     assert func(var) == bool

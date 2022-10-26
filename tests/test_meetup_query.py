#!/usr/bin/env python3

import pandas
# import pytest
import re
import sys
import time
# from icecream import ic
from math import isclose
from pathlib import Path

# import from parent dir
sys.path.append(str(Path(__file__).parent.parent))

# import functions
# from meetup_query import send_request, format_response, sort_csv, sort_json, export_to_file
from meetup_query import *
from sign_jwt import main as gen_token

# import vars from .env
# from decouple import config

tokens = gen_token()
access_token = tokens['access_token']


def test_send_request():
    """
    Test send_request()
    """
    res = send_request(access_token, query, vars)

    # * upstream script returns a string (dict)
    # assert res.status_code == 200

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
    assert df.empty == False


# TODO: not in use currently -- can skip for meow
# def test_sort_csv():
#     """Test sort_csv()"""
#     var = func()
#     assert func(var) == bool


def test_sort_json():
    """Test sort_json()"""
    res = send_request(access_token, query, vars)
    exclusions = ['36\u00b0N', 'Tulsa']
    df = format_response(res, exclusions=exclusions)
    df.to_json("/tmp/test.json", orient='records', force_ascii=False)
    fn = "/tmp/test.json"
    sort_json(fn)

    assert Path(fn).exists() == True
    assert Path(fn).stat().st_size >= 1000
    # TODO: verify first date is sooner than last date
    # "date":"2022-10-13T12:00-05:00" vs. "date":"2022-10-15T14:00-05:00"


# def test_():
#     """Test _()"""
#     var = func()
#     assert func(var) == bool

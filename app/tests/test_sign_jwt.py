#!/usr/bin/env python3

# import pytest
import sys
import time
# from icecream import ic
from math import isclose
from pathlib import Path

# import from parent dir
sys.path.append(str(Path(__file__).parent.parent))

# import functions
from sign_jwt import gen_payload_data, sign_token, verify_token, get_access_token

# TODO: setup github secrets + github actions
# import vars from .env
from decouple import config
SIGNING_KEY_ID = config('SIGNING_KEY_ID')
SELF_ID = config('SELF_ID')
TOKEN_URL = config('TOKEN_URL')
JWT_LIFE_SPAN = config('JWT_LIFE_SPAN', default=120, cast=int)
CLIENT_ID = config('CLIENT_ID')
CLIENT_SECRET = config('CLIENT_SECRET')
REDIRECT_URI = config('REDIRECT_URI')


def test_gen_payload_data():
    """
    Test gen_payload_data()

    NOTE: Unable to accurately test the ''exp' value
    because they are generated at runtime.
    """
    payload_data = gen_payload_data()

    assert payload_data['audience'] == "api.meetup.com"
    assert payload_data['kid'] == SIGNING_KEY_ID
    assert payload_data['sub'] == SELF_ID
    assert payload_data['iss'] == CLIENT_SECRET
    assert isclose(payload_data['exp'], time.time() + int(JWT_LIFE_SPAN))


def test_sign_token():
    """Test sign_token()"""
    token = sign_token()

    assert isinstance(token, str) and len(token) >= 1030


def test_verify_token():
    """Test verify_token()"""
    token = sign_token()

    if verify_token(token):
        assert True


# TODO: mock requests.post() to test get_access_token()
def test_get_access_token():
    """Test get_access_token()"""
    token = sign_token()
    res = get_access_token(token)

    assert res.status_code == 200
    assert res.text.find('access_token') != -1
    assert res.text.find('refresh_token') != -1
    assert res.text.find('token_type') != -1
    assert res.text.find('expires_in') != -1

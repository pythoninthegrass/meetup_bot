#!/usr/bin/env python3

# SOURCE: https://gist.github.com/valeriocos/e16424bc7dc0f2d6dd8bb9295c6f9a4b

import json
import os
import redis
import requests
# import requests_cache
import sys
# import webbrowser
from authlib.integrations.requests_client import OAuth2Session
from datetime import timedelta
from decouple import config
from icecream import ic
from pathlib import Path
from playwright.sync_api import Playwright, sync_playwright
from urllib.parse import urlencode

# verbose icecream
ic.configureOutput(includeContext=True)

# cache the requests as script basename, expire after 1 hour
# requests_cache.install_cache(Path(__file__).stem, expire_after=3600)

# env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()

# creds
if env.exists():
    CLIENT_ID = config('CLIENT_ID')
    CLIENT_SECRET = config('CLIENT_SECRET')
    REDIRECT_URI = config('REDIRECT_URI')
    AUTH_BASE_URL = config('AUTH_BASE_URL')
    TOKEN_URL = config('TOKEN_URL')
    MEETUP_EMAIL = config('MEETUP_EMAIL')
    MEETUP_PASS = config('MEETUP_PASS')
    REDIS_PASS = config('REDIS_PASS')
else:
    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')
    REDIRECT_URI = os.getenv('REDIRECT_URI')
    AUTH_BASE_URL = os.getenv('AUTH_BASE_URL')
    TOKEN_URL = os.getenv('TOKEN_URL')
    MEETUP_EMAIL = os.getenv('MEETUP_EMAIL')
    MEETUP_PASS = os.getenv('MEETUP_PASS')
    REDIS_PASS = os.getenv('REDIS_PASS')


# TODO: replace playwright w/requests
authorization_endpoint = AUTH_BASE_URL
client = OAuth2Session(CLIENT_ID, CLIENT_SECRET, redirect_uri=REDIRECT_URI)
uri, state = client.create_authorization_url(authorization_endpoint, response_type='token')


# TODO: rewrite as a class and replace *code, **grant_type
def get_token_info(endpoint, client_id, client_secret, redirect_uri, *code, **grant_type):
    """Get token info."""
    if code:
        endpoint = endpoint + '?' + urlencode({'client_id': client_id, 'client_secret': client_secret, 'redirect_uri': redirect_uri, 'code': code, 'grant_type': grant_type})
    else:
        endpoint = endpoint + '?' + urlencode({'client_id': client_id, 'client_secret': client_secret, 'redirect_uri': redirect_uri, 'grant_type': grant_type})
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    r = requests.post(endpoint, headers=headers)
    r_json = r.json()

    return r_json


def run(playwright: Playwright) -> None:
    """Simulate a user login."""
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": 'code'
    }
    endpoint = AUTH_BASE_URL
    endpoint = endpoint + '?' + urlencode(params)
    # webbrowser.open(endpoint)

    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto(endpoint)

    page.locator("[data-testid=\"email\"]").click()
    page.locator("[data-testid=\"email\"]").fill(MEETUP_EMAIL)
    page.locator("[data-testid=\"current-password\"]").click()
    page.locator("[data-testid=\"current-password\"]").fill(MEETUP_PASS)

    with page.expect_navigation():
        page.locator("[data-testid=\"submit\"]").click()

    global CODE
    CODE = page.url.split("code=")[1]

    context.close()
    browser.close()

    return CODE


def redis_connect() -> redis.client.Redis:
    try:
        client = redis.Redis(
            host="localhost",
            port=6379,
            password=REDIS_PASS,
            db=0,
            socket_timeout=5,
        )
        ping = client.ping()
        if ping is True:
            return client
    except redis.AuthenticationError:
        print("AuthenticationError")
        sys.exit(1)


client = redis_connect()


def get_routes_from_cache(key):
    """Get cached tokens with expiration times from redis."""
    val = client.get(key)
    exp = client.ttl(key)

    return val, exp


def set_routes_to_cache(key: str, value: str) -> bool:
    """Set data to redis."""
    # TODO: arrow dataerror
    # set data to redis cache with one hour expiration
    state = client.setex(key, timedelta(seconds=3600), value=value)

    return state


def main():
    # look for the data in redis cache
    data = get_routes_from_cache('access_token')

    if data is None:
        with sync_playwright() as playwright:
            run(playwright)

        # TODO: debug optional *code and **grant_type
        # https://www.meetup.com/api/authentication/#p02-server-flow-section
        info = get_token_info(AUTH_BASE_URL, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, CODE, grant_type='authorization_code')

        print(json.dumps(info, sort_keys=True, indent=4))

        token, refresh_token = info['access_token'], info['refresh_token']

        # set the token to redis cache
        set_routes_to_cache('access_token', token)
        set_routes_to_cache('refresh_token', refresh_token)
    # TODO: QA renew bearer token with refresh token: `client.expire('access_token', 5)`
    elif data is not None and data[1] < 0:
        # https://www.meetup.com/api/authentication/#p03-server-flow-section
        info = get_token_info(AUTH_BASE_URL, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, grant_type='refresh_token')

        print(json.dumps(info, sort_keys=True, indent=4))

        token, refresh_token = info['access_token'], info['refresh_token']

        # set the token to redis cache
        set_routes_to_cache('access_token', token)
        set_routes_to_cache('refresh_token', refresh_token)
    else:
        # get the tokens from redis cache and convert to string from bytes
        token = (get_routes_from_cache('access_token'))[0].decode('utf-8')
        refresh_token = (get_routes_from_cache('refresh_token'))[0].decode('utf-8')
        print(f"Retrieved cached tokens\ntoken: {token}\nrefresh_token: {refresh_token}")

    return token, refresh_token


if __name__ == "__main__":
    main()

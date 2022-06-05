#!/usr/bin/env python3

# SOURCE: https://gist.github.com/valeriocos/e16424bc7dc0f2d6dd8bb9295c6f9a4b

# import json
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
    TTL = config('TTL', default=3600, cast=int)
else:
    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')
    REDIRECT_URI = os.getenv('REDIRECT_URI')
    AUTH_BASE_URL = os.getenv('AUTH_BASE_URL')
    TOKEN_URL = os.getenv('TOKEN_URL')
    MEETUP_EMAIL = os.getenv('MEETUP_EMAIL')
    MEETUP_PASS = os.getenv('MEETUP_PASS')
    REDIS_PASS = os.getenv('REDIS_PASS')
    TTL = os.getenv('TTL', default=3600, cast=int)


# TODO: replace playwright w/requests
authorization_endpoint = AUTH_BASE_URL
client = OAuth2Session(CLIENT_ID, CLIENT_SECRET, redirect_uri=REDIRECT_URI)
uri, state = client.create_authorization_url(authorization_endpoint, response_type='token')


def get_token_info(client_id, client_secret, redirect_uri, code):
    endpoint = TOKEN_URL
    endpoint = endpoint + '?' + urlencode({'client_id': client_id, 'client_secret': client_secret, 'redirect_uri': redirect_uri, 'code': code, 'grant_type': 'authorization_code'})
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


# TODO: skip redis if it isn't available
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
    except redis.ConnectionError:
        print("ConnectionError. Start redis to cache tokens.")
        sys.exit(1)
        # pass


def get_routes_from_cache(redis_client, key):
    """Get cached tokens with expiration times from redis."""

    val = redis_client.get(key)
    if val is not None:
        ttl = redis_client.ttl(key)
    else:
        ttl = 0

    return {key: val, 'ttl': ttl}


def set_routes_to_cache(redis_client, key: str, value: str) -> bool:
    """Set data to redis."""
    # set data to redis cache with one hour expiration
    state = redis_client.setex(key, timedelta(seconds=TTL), value=value)

    return state


def renew_token(client_id, client_secret, refresh_token):
    """
    POST to TOKEN_URL with refresh_token

    [HTTPIE]
    http POST https://secure.meetup.com/oauth2/access client_id==$CLIENT_ID client_secret==$CLIENT_SECRET grant_type==refresh_token refresh_token==$refresh_token
    """

    endpoint = TOKEN_URL
    endpoint = endpoint + '?' + urlencode({'client_id': client_id, 'client_secret': client_secret, 'grant_type': 'refresh_token', 'refresh_token': refresh_token})
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    r = requests.post(endpoint, headers=headers)
    r_json = r.json()

    return r_json


def main():
    client = redis_connect()

    # look for the data in redis cache
    access_token = get_routes_from_cache(client, 'access_token')
    refresh_token = get_routes_from_cache(client, 'refresh_token')

    if access_token['access_token'] is None:
        with sync_playwright() as playwright:
            run(playwright)

        info = get_token_info(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, CODE)
        # print(json.dumps(info, sort_keys=True, indent=4))

        ttl = info['expires_in']

        access_token, refresh_token = info['access_token'], info['refresh_token']

        # set the token to redis cache
        set_routes_to_cache(client, 'access_token', access_token)
        set_routes_to_cache(client, 'refresh_token', refresh_token)

        print("Generated tokens\n")
    # renew token if expired or ttl is less than 5 minutes
    elif access_token['ttl'] < 300:
        print("\nRenewing token")
        r_json = renew_token(CLIENT_ID, CLIENT_SECRET, refresh_token['refresh_token'])
        access_token = r_json['access_token']
        refresh_token = r_json['refresh_token']
        ttl = str(r_json['expires_in'])

        # store in redis
        set_routes_to_cache(client, 'access_token', access_token)
        set_routes_to_cache(client, 'refresh_token', refresh_token)

        print("\nRefreshed access token\n")
    else:
        print("Retrieved cached tokens\n")
        ttl = access_token['ttl']
        access_token = access_token['access_token'].decode('utf-8')
        refresh_token = refresh_token['refresh_token'].decode('utf-8')

    # TODO: write func/class/decorator to print dynamically
    print(f"Acc Token: {access_token}")
    print(f"Ref Token: {refresh_token}")
    print(f"\nAccess token TTL: {ttl} seconds remaining\n")

    return access_token, refresh_token


if __name__ == "__main__":
    main()

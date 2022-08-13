#!/usr/bin/env python3

import os
import redis
import requests
import sys
# import time
from authlib.integrations.requests_client import OAuth2Session
from datetime import timedelta
from decouple import config
# from icecream import ic
from pathlib import Path
from playwright.sync_api import Playwright, sync_playwright
# from playwright.async_api import async_playwright
from python_on_whales import docker, DockerClient
from urllib.parse import urlencode

# verbose icecream
# ic.configureOutput(includeContext=True)

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
    REDIS_URL: config('REDIS_URL', default=None)
    REDIS_PASS = config('REDIS_PASS')
    TTL = config('TTL', default=3600, cast=int)
    HOST = config('HOST', default='localhost')
else:
    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')
    REDIRECT_URI = os.getenv('REDIRECT_URI')
    AUTH_BASE_URL = os.getenv('AUTH_BASE_URL')
    TOKEN_URL = os.getenv('TOKEN_URL')
    MEETUP_EMAIL = os.getenv('MEETUP_EMAIL')
    MEETUP_PASS = os.getenv('MEETUP_PASS')
    REDIS_URL = os.getenv('REDIS_URL')
    REDIS_PASS = os.getenv('REDIS_PASS')
    TTL = os.getenv('TTL', default=3600)
    HOST = os.getenv('HOST', default='localhost')


# override host env var if system is macos
if sys.platform == 'darwin':
    HOST = 'localhost'

# TODO: replace playwright w/requests
authorization_endpoint = AUTH_BASE_URL
client = OAuth2Session(CLIENT_ID, CLIENT_SECRET, redirect_uri=REDIRECT_URI)
uri, state = client.create_authorization_url(authorization_endpoint, response_type='token')


def start_docker(yml_file=None):
    """Start docker."""

    # project_config = docker.compose.config()
    if yml_file is not None:
        docker = DockerClient(compose_files=[Path(yml_file)])
        if docker.container.list(all=False) == []:
            docker.compose.up(
                services=['redis', 'redisinsight'],
                build=False,
                detach=True,
            )
    elif yml_file is None:
        if docker.container.list(all=False):
            docker.compose.up(
                services=['redis', 'redisinsight'],
                build=False,
                detach=True,
            )
    else:
        print("Docker is already running")


def stop_docker():
    """Stop docker."""
    docker.compose.stop(
        services=None,
    )


def get_token_info(client_id, client_secret, redirect_uri, code):
    """Get token info from Meetup."""

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

    try:
        browser = playwright.firefox.launch(headless=True)
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
    except Exception as e:
        print(f"{e}. Try running `python -m playwright install firefox`")
        context.close()
        browser.close()

    return CODE


# TODO: test REDIS_URL in heroku
def redis_connect() -> redis.client.Redis:
    """Connect to redis."""

    try:
        if sys.platform == 'darwin':
            client = redis.Redis(host=HOST, port=6379, password=REDIS_PASS, db=0, socket_timeout=5)
        else:
            client = redis.from_url(REDIS_URL, db=0, socket_timeout=5)
        ping = client.ping()
        if ping is True:
            return client
    except redis.AuthenticationError:
        print("AuthenticationError")
        sys.exit(1)
    except redis.ConnectionError:
        print("ConnectionError. Start redis to cache tokens.")
        sys.exit(1)


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
    """Run the main function."""

    # override host env var if system is macos
    if HOST == 'localhost':
        # start containers (only build if images aren't present)
        start_docker(yml_file='docker-compose.yml')

    # initialize redis client
    client = redis_connect()

    # look for the data in redis cache
    access_token = get_routes_from_cache(client, 'access_token')
    refresh_token = get_routes_from_cache(client, 'refresh_token')

    # run playwright if no data in redis cache
    if access_token['access_token'] is None:
        with sync_playwright() as playwright:
            run(playwright)

        info = get_token_info(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, CODE)

        ttl = info['expires_in']

        access_token, refresh_token = info['access_token'], info['refresh_token']

        # set the token to redis cache
        set_routes_to_cache(client, 'access_token', access_token)
        set_routes_to_cache(client, 'refresh_token', refresh_token)

        print("[INFO] Generated tokens")
    # renew token if expired or ttl is less than 5 minutes
    elif access_token['ttl'] <= 300:
        print("[INFO] Renewing token")
        r_json = renew_token(CLIENT_ID, CLIENT_SECRET, refresh_token['refresh_token'])
        access_token = r_json['access_token']
        refresh_token = r_json['refresh_token']
        ttl = str(r_json['expires_in'])

        # store in redis
        set_routes_to_cache(client, 'access_token', access_token)
        set_routes_to_cache(client, 'refresh_token', refresh_token)

        print("[INFO] Refreshed access token")
    else:
        print("[INFO] Retrieved cached tokens")
        ttl = access_token['ttl']
        access_token = access_token['access_token'].decode('utf-8')
        refresh_token = refresh_token['refresh_token'].decode('utf-8')

    # TODO: comment out in prod
    # print(f"[DEBUG] Acc Token: {access_token}")
    # print(f"[DEBUG] Ref Token: {refresh_token}")
    print(f"[INFO] Access token TTL: {ttl} seconds remaining")

    return access_token, refresh_token


if __name__ == "__main__":
    access_token, refresh_token = main()

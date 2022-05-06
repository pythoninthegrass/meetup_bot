#!/usr/bin/env python3

# SOURCE: https://gist.github.com/valeriocos/e16424bc7dc0f2d6dd8bb9295c6f9a4b

import json
import os
import requests
import requests_cache
from decouple import config
from icecream import ic
from pathlib import Path
from playwright.sync_api import Playwright, sync_playwright

# TODO: switch to `meetup-client` and `meetup-token-manager`

# verbose icecream
ic.configureOutput(includeContext=True)

# cache the requests as script basename
requests_cache.install_cache(Path(__file__).stem, expire_after=3600)

# env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()

# creds
if env.exists():
    CLIENT_KEY = config('CLIENT_KEY')
    CLIENT_SECRET = config('CLIENT_SECRET')
    REDIRECT_URI = config('REDIRECT_URI')
    MEETUP_EMAIL = config('MEETUP_EMAIL')
    MEETUP_PASS = config('MEETUP_PASS')
else:
    CLIENT_KEY = os.getenv('CLIENT_KEY')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')
    REDIRECT_URI = os.getenv('REDIRECT_URI')
    MEETUP_EMAIL = os.getenv('MEETUP_EMAIL')
    MEETUP_PASS = os.getenv('MEETUP_PASS')

OAUTH_AUTHORIZE_URL = "https://secure.meetup.com/oauth2/authorize?client_id={}&redirect_uri={}&response_type=code"
OAUTH2_TOKEN_URL = 'https://secure.meetup.com/oauth2/access?client_id={}&client_secret={}&redirect_uri={}&code={}&grant_type=authorization_code'


def get_token_info(client_id, client_secret, redirect_uri, code):
    access_uri = OAUTH2_TOKEN_URL.format(client_id, client_secret, redirect_uri.strip("\""), code)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    r = requests.post(access_uri, headers=headers)
    r_json = r.json()

    return r_json


# TODO: setup httpbin/ngrok/tolocalhost.com
def gen_url():
    """
    This script assists the user to generate an OAuth2 token to access the
    meetup API. It requires the package requests.
    An example of execution is provided below:

    Enter your consumer key: 5eeqs...
    Redirect URI (between quotes): "https://example.com/test"
    https://secure.meetup.com/oauth2/authorize?client_id=5eeqs4f5h...&redirect_uri=https://example.com/test&response_type=code
    Access the URL below, authorize the application, and get the code that appears on the URL
    Enter the code: d33fd...
    Enter your consumer secret: 1o39i...
    ***** token *****
    {
        "access_token": "67bd7...",
        "expires_in": 3600,
        "refresh_token": "c6e13...",
        "token_type": "bearer"
    }
    """
    global url
    url = OAUTH_AUTHORIZE_URL.format(CLIENT_KEY, REDIRECT_URI.strip("\""))

    return url


def run(playwright: Playwright) -> None:
    gen_url()

    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto(url)

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


def main():
    with sync_playwright() as playwright:
        run(playwright)

    # CODE = input('Enter the code: ')
    info = get_token_info(CLIENT_KEY, CLIENT_SECRET, REDIRECT_URI, CODE)

    print("***** access_token *****")
    print(json.dumps(info, sort_keys=True, indent=4))

    # extract access_token
    return info['access_token']


if __name__ == "__main__":
    main()

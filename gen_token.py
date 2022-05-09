#!/usr/bin/env python3

# SOURCE: https://gist.github.com/valeriocos/e16424bc7dc0f2d6dd8bb9295c6f9a4b

import json
import os
import requests
# import requests_cache
import webbrowser
from decouple import config
from icecream import ic
from pathlib import Path
from playwright.sync_api import Playwright, sync_playwright
from requests_oauthlib import OAuth2Session
from urllib.parse import urlencode

# verbose icecream
ic.configureOutput(includeContext=True)

# cache the requests as script basename
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
else:
    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')
    REDIRECT_URI = os.getenv('REDIRECT_URI')
    AUTH_BASE_URL = os.getenv('AUTH_BASE_URL')
    TOKEN_URL = os.getenv('TOKEN_URL')
    MEETUP_EMAIL = os.getenv('MEETUP_EMAIL')
    MEETUP_PASS = os.getenv('MEETUP_PASS')


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


# TODO: setup httpbin/ngrok/tolocalhost.com
def run(playwright: Playwright) -> None:
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


def main():
    with sync_playwright() as playwright:
        run(playwright)

    info = get_token_info(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, CODE)

    print("***** access_token *****")
    print(json.dumps(info, sort_keys=True, indent=4))

    # extract access_token and refresh_token
    return info['access_token'], info['refresh_token']


if __name__ == "__main__":
    main()

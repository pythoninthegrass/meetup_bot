#!/usr/bin/env python3

# SOURCE:https://gist.github.com/valeriocos/e16424bc7dc0f2d6dd8bb9295c6f9a4b

import json
import os
import requests
from decouple import config
from pathlib import Path

# env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()

# creds
if env.exists():
    MEETUP_KEY = config('MEETUP_KEY')
    MEETUP_SECRET = config('MEETUP_SECRET')
    REDIRECT_URI = config('REDIRECT_URI')
else:
    MEETUP_KEY = os.getenv('MEETUP_KEY')
    MEETUP_SECRET = os.getenv('MEETUP_SECRET')
    REDIRECT_URI = os.getenv('REDIRECT_URI')

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


# TODO: setup ngrok or https://tolocalhost.com/ && use headless playwright and/or just requests to get `access_token`
def main():
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
    url = OAUTH_AUTHORIZE_URL.format(MEETUP_KEY, REDIRECT_URI.strip("\""))
    print(url)

    """Moved to access_token.py"""
    # print("Access the URL below, authorize the application, and get the code that appears on the URL")

    # CODE = input('Enter the code: ')
    # info = get_token_info(MEETUP_KEY, MEETUP_SECRET, REDIRECT_URI, CODE)

    # print("***** token *****")
    # print(json.dumps(info, sort_keys=True, indent=4))


if __name__ == "__main__":
    main()

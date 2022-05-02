#!/usr/bin/env python3

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

auth_url = f"https://secure.meetup.com/oauth2/authorize?client_id={MEETUP_KEY}&response_type=code&redirect_uri={REDIRECT_URI}"
token_url = f"https://secure.meetup.com/oauth2/access"

endpoint = f"https://graphql.contentful.com/content/v1/spaces/{spaceID}"
headers = {"Authorization": f"Bearer {accessToken}"}

query = """query {
  showCollection{
    items {
      title
      firstEpisodeDate
      lastEpisodeDate
      henshinMp4 {
        url
      }
    }
  }
}"""

r = requests.post(endpoint, json={"query": query}, headers=headers)
if r.status_code == 200:
    print(json.dumps(r.json(), indent=2))
else:
    raise Exception(f"Query failed to run with a {r.status_code}.")

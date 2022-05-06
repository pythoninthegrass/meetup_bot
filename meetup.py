#!/usr/bin/env python3

import json
import requests
# import requests_cache
# from decouple import config
from gen_token import main as gen_token
from icecream import ic
from pathlib import Path
from pprint import pprint

# verbose icecream
ic.configureOutput(includeContext=True)

# cache the requests as script basename
# requests_cache.install_cache(Path(__file__).stem)

query = """
query {
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
}
"""
vars = '{ "id": "364335959210266624" }'
endpoint = 'https://api.meetup.com/gql'
headers = {
    'Authorization': 'Bearer {}'.format(gen_token()),
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

r = requests.post(
    endpoint,
    json={"query": query, "variables": vars},
    headers=headers
)

if r.status_code == 200:
    print(json.dumps(r.json(), indent=2))
else:
    # format the error message
    formatted_error = '{}:\n\n{}'.format(r.status_code, r.json()['errors'][0]['message'])
    raise Exception(
        f"Query failed to run returning status code {formatted_error}"
    )

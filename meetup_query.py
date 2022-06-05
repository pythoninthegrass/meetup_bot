#!/usr/bin/env python3

# import arrow
import json
# import os
import pandas as pd
import requests
import requests_cache
import sys
# from decouple import config
from gen_token import main as gen_token
from icecream import ic
from pathlib import Path
# from pprint import pprint

# verbose icecream
ic.configureOutput(includeContext=True)

# cache the requests as script basename, expire after 1 hour
requests_cache.install_cache(Path(__file__).stem, expire_after=3600)

# env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()

# import bearer token from gen_token.py main function (tuple index 0)
tokens = gen_token()
token = tokens[0]
refresh_token = tokens[1]

# TODO: move query and vars to gql file
query = """
query($id: ID!) {
  proNetwork(id: $id) {
    eventsSearch(filter: { status: UPCOMING }, input: { first: 25 }) {
      count
      pageInfo {
        endCursor
      }
      edges {
        node {
          id
          title
          description
          dateTime
          eventUrl
        }
      }
    }
  }
}
"""

vars = '{ "id": "364335959210266624" }'
endpoint = 'https://api.meetup.com/gql'

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json; charset=utf-8'
}


def send_request():
    """
    Request
    POST https://api.meetup.com/gql
    """

    try:
        r = requests.post(
            endpoint,
            json={'query': query, 'variables': vars},
            headers=headers
        )
        print('Response HTTP Status Code: {status_code}'.format(status_code=r.status_code))

        # pretty prints json response content but skips sorting keys as it rearranges graphql response
        pretty_response = json.dumps(r.json(), indent=2, sort_keys=False)

        # formatted response
        print('Response HTTP Response Body:\n{content}'.format(content=pretty_response))
    except requests.exceptions.RequestException as e:
        print('HTTP Request failed:\n{error}'.format(error=e))
        sys.exit(1)

    return pretty_response


# TODO: skip export in prod
def main():
    # run function only
    # send_request()

    # create directory if it doesn't exist
    Path('raw').mkdir(parents=True, exist_ok=True)

    # export to raw/output.json with pandas
    df = pd.read_json(send_request())
    df.to_json('raw/output.json')


if __name__ == '__main__':
    main()

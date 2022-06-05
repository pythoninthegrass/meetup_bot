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

# search all affiliate groups for upcoming events (node doesn't expose name of affiliate group)
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
# shorthand for proNetwork id
vars = '{ "id": "364335959210266624" }'


def send_request(token):
    """
    Request
    POST https://api.meetup.com/gql
    """

    endpoint = 'https://api.meetup.com/gql'

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json; charset=utf-8'
    }

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


def export_to_file(response, type):
    """
    Export to CSV or JSON
    """

    # convert response to json
    response_json = json.loads(response)

    # extract data from json
    data = response_json['data']['proNetwork']['eventsSearch']['edges']

    # create dataframe
    df = pd.DataFrame(data)

    # create directory if it doesn't exist
    Path('raw').mkdir(parents=True, exist_ok=True)

    if type == 'csv':
        df.to_csv(Path('raw/output.csv'), index=False)
    elif type == 'json':
        df.to_json(Path('raw/output.json'), orient='records')
    else:
        print('Invalid export file type')


def main():
    # import bearer token from gen_token.py main function (tuple index 0)
    tokens = gen_token()
    token = tokens[0]
    # refresh_token = tokens[1]

    response = send_request(token)

    export_to_file(response, 'json')             # skip export in prod


if __name__ == '__main__':
    main()

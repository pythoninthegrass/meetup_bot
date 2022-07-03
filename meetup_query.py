#!/usr/bin/env python3

import arrow
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
query {
    self {
        id
        name
        username
        memberUrl
        upcomingEvents {
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
                    group {
                        id
                        name
                        urlname
                        link
                        city
                    }
                }
            }
        }
    }
}
"""
# shorthand for proNetwork id (unused in `self` query, but required in headers)
vars = '{ "id": "364335959210266624" }'

url_query = """
query($urlname: String!) {
    groupByUrlname(urlname: $urlname) {
        id
        description
        name
        urlname
        city
        link
        upcomingEvents(input: { first: 1 }) {
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
                    group {
                        id
                        name
                        urlname
                        link
                        city
                    }
                }
            }
        }
    }
}
"""

# read groups from file via pandas
csv = pd.read_csv('raw/groups.csv', header=0)

# remove `techlahoma-foundation` row
sans_tf = csv[csv['urlname'] != 'techlahoma-foundation']

# remove url column
groups = sans_tf.drop(columns=['url'])

# read groups `_values`
groups_array = groups['urlname']._values

# assign to `url_vars` as a list
url_vars = [group for group in groups_array]


def send_request(token, query, vars):
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
        print('Response HTTP Status Code: {status_code}\n'.format(status_code=r.status_code))

        # pretty prints json response content but skips sorting keys as it rearranges graphql response
        pretty_response = json.dumps(r.json(), indent=2, sort_keys=False)

        # formatted response
        # print('Response HTTP Response Body:\n{content}'.format(content=pretty_response))
    except requests.exceptions.RequestException as e:
        print('HTTP Request failed:\n{error}'.format(error=e))
        sys.exit(1)

    return pretty_response


# TODO: sort json keys (cf. `orient='records'` on `df.to_json` export), format response for slack
def format_response(response, location='Oklahoma City'):
    """
    Format response for Slack
    """

    # convert response to json
    response_json = json.loads(response)

    # extract data from json
    try:
        data = response_json['data']['self']['upcomingEvents']['edges']
    except KeyError:
        data = response_json['data']['groupByUrlname']['upcomingEvents']['edges']

    # if city is missing, raise error
    if data[0]['node']['group']['city'] != location:
        raise ValueError(f'No data for {location} found')

    # pandas don't truncate output
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)

    # create dataframe with columns name, data, title, description, event url
    df = pd.DataFrame(data, columns=['name', 'date', 'title', 'description', 'city', 'eventUrl'])

    # append data to rows
    for i in range(len(data)):
        df.loc[i, 'name'] = data[i]['node']['group']['name']
        df.loc[i, 'date'] = data[i]['node']['dateTime']
        df.loc[i, 'title'] = data[i]['node']['title']
        df.loc[i, 'description'] = data[i]['node']['description']
        df.loc[i, 'city'] = data[i]['node']['group']['city']
        df.loc[i, 'eventUrl'] = data[i]['node']['eventUrl']

    # drop rows that aren't in a specific city
    df = df[df['city'] == location]

    # drop rows that aren't within the next 7 days
    time_span = arrow.now().shift(days=7)
    df = df[df['date'] <= time_span.isoformat()]

    # convert date to human readable format (Thu 5/26 at 11:30 am)
    df['date'] = df['date'].apply(lambda x: arrow.get(x).format('M/D h:mm a'))

    return df


def export_to_file(response, type):
    """
    Export to CSV or JSON
    """

    df = format_response(response)

    # create directory if it doesn't exist
    Path('raw').mkdir(parents=True, exist_ok=True)

    if type == 'csv':
        df.to_csv(Path('raw/output.csv'), index=False)
    elif type == 'json':
        # convert escaped unicode to utf-8 encoding
        data = json.loads(df.to_json(orient='records', force_ascii=False))

        with open('raw/output.json', 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, sort_keys=False)
    else:
        print('Invalid export file type')


# TODO: disable in prod (use `main.py`)
def main():
    tokens = gen_token()
    token = tokens[0]

    response = send_request(token, query, vars)

    format_response(response)

    export_to_file(response, 'json')   # csv/json


if __name__ == '__main__':
    main()

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

# TODO: format response for slack, query third-party groups
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


def format_response(response):
    """
    Format response for Slack
    """

    # convert response to json
    response_json = json.loads(response)

    # extract data from json
    data = response_json['data']['self']['upcomingEvents']['edges']

    # loop through data and format for Slack
    # for i in range(len(data)):
    #     print(f'{data[i]["node"]["group"]["name"]}')    # group name
    #     print(f'{data[i]["node"]["dateTime"]}')         # date
    #     print(f'{data[i]["node"]["title"]}')            # title
    #     print(f'{data[i]["node"]["description"]}')      # description
    #     print(f'{data[i]["node"]["group"]["city"]}')    # city
    #     print(f'{data[i]["node"]["eventUrl"]}\n')       # event url

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

    # drop rows that aren't located in Oklahoma City
    df = df[df['city'] == 'Oklahoma City']

    # convert date to human readable format (Thu 5/26 at 11:30 am)
    df['date'] = df['date'].apply(lambda x: arrow.get(x).format('M/D h:mm a'))

    # drop rows that aren't within the next 7 days
    time_span = arrow.now().shift(days=7)
    df = df[df['date'] <= time_span.format('M/D/YYYY')]

    ic(df)

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
        df.to_json(Path('raw/output.json'), indent=2, orient='records')
    else:
        print('Invalid export file type')


def main():
    tokens = gen_token()
    token = tokens[0]
    # refresh_token = tokens[1]

    response = send_request(token)

    format_response(response)

    export_to_file(response, 'json')             # csv/json (skip export in prod)


if __name__ == '__main__':
    main()

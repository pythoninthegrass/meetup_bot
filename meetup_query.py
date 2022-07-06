#!/usr/bin/env python3

import arrow
import json
import os
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

# pandas don't truncate output
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

# cache the requests as script basename, expire after 1 hour
requests_cache.install_cache(Path(__file__).stem, expire_after=3600)

# env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()
format = 'json'
csv_fn = Path('raw/output.csv')
json_fn = Path('raw/output.json')
groups_csv = Path('raw/groups.csv')

# read groups from file via pandas
csv = pd.read_csv(groups_csv, header=0)

# remove `techlahoma-foundation` row
sans_tf = csv[csv['urlname'] != 'techlahoma-foundation']

# remove url column
groups = sans_tf.drop(columns=['url'])

# read groups `_values`
groups_array = groups['urlname']._values

# assign to `url_vars` as a list
url_vars = [group for group in groups_array]

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


def format_response(response, location='Oklahoma City'):
    """
    Format response for Slack
    """

    # convert response to json
    response_json = json.loads(response)

    # extract data from json and if city is missing, raise error
    try:
        data = response_json['data']['self']['upcomingEvents']['edges']
        if data[0]['node']['group']['city'] != location:
            raise ValueError(f'No data for {location} found')
    except KeyError:
        data = response_json['data']['groupByUrlname']['upcomingEvents']['edges']
        # TODO: handle no upcoming events to fallback on initial response
        if response_json['data']['groupByUrlname']['city'] != location:
            raise ValueError(f'No data for {location} found')

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

    return df


# TODO: QA
def sort_csv(filename):
    """
    Sort CSV by date
    """

    # read csv
    df = pd.read_csv(filename, header=0)

    # drop duplicates by event url
    df = df.drop_duplicates(subset='eventUrl')

    # sort by date
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['date'])

    # convert date to human readable format (Thu 5/26 at 11:30 am)
    df['date'] = df['date'].apply(lambda x: arrow.get(x).format('ddd M/D h:mm a'))

    # write csv
    df.to_csv(filename, index=False)


def sort_json(filename):
    """
    Sort JSON keys
    """

    # pandas remove duplicate keys by eventUrl key
    df = pd.read_json(filename, orient='records')
    df = df.drop_duplicates(subset='eventUrl')

    # sort by date
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['date'])

    # convert date to human readable format (Thu 5/26 at 11:30 am)
    df['date'] = df['date'].apply(lambda x: arrow.get(x).format('ddd M/D h:mm a'))

    # export to json (convert escaped unicode to utf-8 encoding first)
    data = json.loads(df.to_json(orient='records', force_ascii=False))
    with open(json_fn, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def export_to_file(response, type='json'):
    """
    Export to CSV or JSON
    """

    df = format_response(response)

    # create directory if it doesn't exist
    Path('raw').mkdir(parents=True, exist_ok=True)

    if type == 'csv':
        df.to_csv(Path(csv_fn), mode='a', header=False, index=False)
    elif type == 'json':
        # convert escaped unicode to utf-8 encoding
        data = json.loads(df.to_json(orient='records', force_ascii=False))

        # write json to file
        # if file exists, is less than an hour old, and is not empty, append to file
        if (
            Path(json_fn).exists()
            and (arrow.now() - arrow.get(os.path.getmtime(json_fn))).seconds < 3600
            and os.stat(json_fn).st_size > 0
        ):
            # append to json
            with open(json_fn, 'r') as f:
                data_json = json.load(f)
                data_json.extend(data)
                with open(json_fn, 'w', encoding='utf-8') as f:
                    json.dump(data_json, f, indent=2)
        else:
            # create/overwrite json
            with open(json_fn, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
    else:
        print('Invalid export file type')


# TODO: disable in prod (use `main.py`)
def main():
    tokens = gen_token()
    token = tokens[0]

    # first-party query
    response = send_request(token, query, vars)
    # format_response(response)                 # don't need if exporting to file
    export_to_file(response, format)             # csv/json

    # third-party query
    output = []
    for url in url_vars:
        response = send_request(token, url_query, f'{{"urlname": "{url}"}}')
        # append to output dict if the response is not empty
        if len(format_response(response)) > 0:
            output.append(response)
        else:
            print(f'No upcoming events for {url} found\n')
    # loop through output and append to file
    for i in range(len(output)):
        export_to_file(output[i], format)

    # cleanup output file
    if format == 'csv':
        sort_csv(csv_fn)
    elif format == 'json':
        sort_json(json_fn)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3

import arrow
import json
import os
import pandas as pd
import re
import requests
# import requests_cache
import sys
from arrow import ParserError
from colorama import Fore
from sign_jwt import main as gen_token
# from icecream import ic
from pathlib import Path

# verbose icecream
# ic.configureOutput(includeContext=True)

# logging prefixes
info = "INFO:"
error = "ERROR:"
warning = "WARNING:"

# pandas don't truncate output
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

# time span (e.g., 3600 = 1 hour)
sec = int(60)           # n seconds
age = int(sec * 1)      # n minutes -> hours

# cache the requests as script basename, expire after 1 hour
# requests_cache.install_cache(Path(__file__).stem, expire_after=age)

# env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()
format = 'json'
csv_fn = Path('/tmp/output.csv')
json_fn = Path('/tmp/output.json')
groups_csv = Path('groups.csv')

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

# unaffiliated groups
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
        print(f"{Fore.GREEN}{info:<10}{Fore.RESET}Response HTTP Response Body: {r.status_code}")

        # pretty prints json response content but skips sorting keys as it rearranges graphql response
        pretty_response = json.dumps(r.json(), indent=2, sort_keys=False)

        # formatted response
        # print('Response HTTP Response Body:\n{content}'.format(content=pretty_response))
    except requests.exceptions.RequestException as e:
        print('HTTP Request failed:\n{error}'.format(error=e))
        sys.exit(1)

    return pretty_response

# optional exclusion string parameter
def format_response(response, location='Oklahoma City', exclusions=''):
    """
    Format response for Slack
    """

    # convert response to json
    response_json = json.loads(response)

    # TODO: print skipped events
    # extract data from json
    try:
        data = response_json['data']['self']['upcomingEvents']['edges']
        if data[0]['node']['group']['city'] != location:
            print(f"{Fore.YELLOW}{warning:<10}{Fore.RESET}Skipping event outside of {location}")
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

    # filter rows by city
    df = df[df['city'] == location]

    # TODO: control for mislabeled event locations (e.g. 'Techlahoma Foundation')
    # filtered rows to exclude keywords by regex OR operator
    if exclusions:
        print(f"{Fore.GREEN}{info:<10}{Fore.RESET}Excluded keywords: {exclusions}".format(exclusions=exclusions))
        df = df[~df['name'].str.contains('|'.join(exclusions))]
        df = df[~df['title'].str.contains('|'.join(exclusions))]

    # TODO: cutoff time by day _and_ hour (currently only day)
    # filter rows that aren't within the next 7 days
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

    # replace '1-07-19 17:00:00' with current year '2022-07-19 17:00:00' via regex
    # * negative lookahead only matches first digit at the beginning of the line (e.g., 1/0001 vs. 2022)
    date_regex = r'^1(?![\d])|^0001(?![\d])'

    # TODO: get precise date from event to determine year
    # choose current year if 7 days from now is before EOY
    if arrow.now().year == arrow.now().shift(days=7).year:
        year = str(arrow.now().year)
    else:
        year = str(arrow.now().shift(days=7).year)

    # TODO: log decorator
    # convert date column from 'ddd M/D h:mm a' (e.g., Tue 7/19 5:00 pm) to iso8601
    try:
        df['date'] = df['date'].apply(lambda x: arrow.get(x, 'ddd M/D h:mm a').format('YYYY-MM-DDTHH:mm:ss'))
        df['date'] = df['date'].apply(lambda x: x.replace(re.findall(date_regex, x)[0], year))
    except ParserError:
        print(f"{Fore.RED}{error:<10}{Fore.RESET}ParserError: date column is already in correct format")
        pass
    df['date'] = pd.to_datetime(df['date'])

    # sort by date
    df = df.sort_values(by=['date'])

    # TODO: control for timestamp edge case `1-07-21 18:00:00` raising OutOfBoundsError
    # convert date to human readable format (Thu 5/26 at 11:30 am)
    df['date'] = df['date'].apply(lambda x: arrow.get(x).format('ddd M/D h:mm a'))

    # TODO: store json output in redis
    # export to json (convert escaped unicode to utf-8 encoding first)
    data = json.loads(df.to_json(orient='records', force_ascii=False))
    with open(json_fn, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def export_to_file(response, type='json', exclusions=''):
    """
    Export to CSV or JSON
    """

    if exclusions:
        df = format_response(response, exclusions=exclusions)
    else:
        df = format_response(response)

    # create directory if it doesn't exist
    Path('raw').mkdir(parents=True, exist_ok=True)

    if type == 'csv':
        df.to_csv(Path(csv_fn), mode='a', header=False, index=False)
    elif type == 'json':
        # convert escaped unicode to utf-8 encoding
        data = json.loads(df.to_json(orient='records', force_ascii=False))

        # write json to file
        # if file exists, is less than n minutes old, append to file
        if (
            Path(json_fn).exists()
            and (arrow.now() - arrow.get(os.path.getmtime(json_fn))).seconds < age
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
    access_token = tokens['access_token']
    refresh_token = tokens['refresh_token']

    # TODO: control for descriptions and incorrect city locations (cf. 'Tulsa Techlahoma Night')
    # exclude keywords in event name and title (will miss events with keyword in description)
    exclusions = ['36\u00b0N', 'Tulsa']

    # TODO: reduce `format_response` calls to 1
    # first-party query
    response = send_request(access_token, query, vars)
    # format_response(response, exclusions=exclusions)                      # don't need if exporting to file
    export_to_file(response, format, exclusions=exclusions)                  # csv/json

    # third-party query
    output = []
    for url in url_vars:
        response = send_request(access_token, url_query, f'{{"urlname": "{url}"}}')
        # append to output dict if the response is not empty
        if len(format_response(response, exclusions=exclusions)) > 0:
            output.append(response)
        else:
            print(f'[INFO] No upcoming events for {url} found')
    # loop through output and append to file
    for i in range(len(output)):
        export_to_file(output[i], format)

    # cleanup output file
    if format == 'csv':
        sort_csv(csv_fn)
    elif format == 'json':
        sort_json(json_fn)

    return response


if __name__ == '__main__':
    main()

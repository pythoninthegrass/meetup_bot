#!/usr/bin/env python3

import arrow
import json
import os
import pandas as pd
import requests
import requests_cache
import sys
from arrow import ParserError
from colorama import Fore
from decouple import config
from icecream import ic
from sign_jwt import main as gen_token
from pathlib import Path

# verbose icecream
ic.configureOutput(includeContext=True)

# logging prefixes
info = "INFO:"
error = "ERROR:"
warning = "WARNING:"

# pandas don't truncate output
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

# env
home: Path = Path.home()
cwd: Path = Path.cwd()
format = 'json'
cache_fn = config('CACHE_FN', default='raw/meetup_query')
csv_fn = config('CSV_FN', default='raw/output.csv')
json_fn = config('JSON_FN', default='raw/output.json')
groups_csv = Path('groups.csv')
DAYS = config('DAYS', default=7, cast=int)
tz = config('TZ', default='America/Chicago')

# time span (e.g., 3600 = 1 hour)
sec = int(60)               # n seconds
ttl = int(sec * 30)         # n minutes -> hours

# cache the requests as script basename, expire after n time
requests_cache.install_cache(Path(cache_fn), expire_after=ttl)

# TODO: fix mocker patch for groups_csv
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

# Techlahoma: search all affiliate groups for upcoming events (node doesn't expose name of affiliate group)
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


def send_request(token, query, vars) -> str:
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
def format_response(response, location: str = "Oklahoma City", exclusions: str = ""):
    """
    Format response for Slack
    """

    # create dataframe columns
    df = pd.DataFrame(columns=['name', 'date', 'title', 'description', 'city', 'eventUrl'])

    # convert response to json
    response_json = json.loads(response)

    # TODO: add arg for `self` or `groupByUrlname`
    # extract data from json
    try:
        data = response_json['data']['self']['upcomingEvents']['edges']
        if data[0]['node']['group']['city'] != location:
            print(f"{Fore.YELLOW}{warning:<10}{Fore.RESET}Skipping event outside of {location}")
    except KeyError:
        if response_json['data']['groupByUrlname'] is None:
            data = ""
            print(f"{Fore.YELLOW}{warning:<10}{Fore.RESET}Skipping group due to empty response")
            pass
        else:
            data = response_json['data']['groupByUrlname']['upcomingEvents']['edges']
            # TODO: handle no upcoming events to fallback on initial response
            if response_json['data']['groupByUrlname']['city'] != location:
                print(f"{Fore.RED}{error:<10}{Fore.RESET}No data for {location} found")
                pass

    # append data to rows
    if data is not None:
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
    # TODO: exclude by `urlname` instead of `name`
    # * data[0]['node']['group']['urlname'] == 'nerdygirlsokc'
    # filtered rows to exclude keywords by regex OR operator
    if exclusions:
        print(f"{Fore.GREEN}{info:<10}{Fore.RESET}Excluded keywords: {exclusions}".format(exclusions=exclusions))
        df = df[~df['name'].str.contains('|'.join(exclusions))]
        df = df[~df['title'].str.contains('|'.join(exclusions))]

    # TODO: cutoff time by day _and_ hour (currently only day)
    # filter rows that aren't within the next n days
    time_span = arrow.now(tz=tz).shift(days=DAYS)
    df = df[df['date'] <= time_span.isoformat()]

    return df


# TODO: QA
def sort_csv(filename) -> None:
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


def sort_json(filename) -> None:
    """
    Sort JSON keys
    """

    # pandas remove duplicate keys by eventUrl key
    df = pd.read_json(filename, orient='records')
    df = df.drop_duplicates(subset='eventUrl')

    # replace '1-07-19 17:00:00' with current year '2022-07-19 17:00:00' via regex
    # * negative lookahead only matches first digit at the beginning of the line (e.g., 1/0001 vs. 2022)
    # date_regex = r'^1(?![\d])|^0001(?![\d])'

    # TODO: get precise date from event to determine year
    # choose current year if 7 days from now is before EOY
    # if arrow.now().year == arrow.now().shift(days=7).year:
    #     year = str(arrow.now(TZ).year)
    # else:
    #     year = str(arrow.now(TZ).shift(days=7).year)

    # convert date column from 'ddd M/D h:mm a' (e.g., Tue 7/19 5:00 pm) to iso8601
    try:
        # extract dates from date column into a dictionary
        # * Timestamp('2023-02-28 16:30:00-0600', tz='pytz.FixedOffset(-360)')
        dates = df['date'].to_dict()

        # convert dates to iso8601
        for key, value in dates.items():
            dates[key] = arrow.get(value, 'ddd M/D h:mm a').format('YYYY-MM-DDTHH:mm:ss')

        # replace dates in dictionary with iso8601
        df['date'] = df['date'].replace(dates)
    except ParserError:
        print(f"{Fore.RED}{error:<10}{Fore.RESET}ParserError: date column is already in correct format")
        pass

    # control for timestamp edge case `1-07-21 18:00:00` || `1-01-25 10:00:00` raising OutOfBoundsError
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # convert datetimeindex to datetime
    df['date'] = df['date'].dt.tz_localize(None)

    # replace NaT with epoch time to avoid float TypeError
    df['date'] = df['date'].apply(lambda x: x.replace(year=1970, month=1, day=1) if pd.isnull(x) else x)

    # sort by date
    df = df.sort_values(by=['date'])

    # drop events by date when they are older than the current time
    df = df[df['date'] >= arrow.now(tz).format('YYYY-MM-DDTHH:mm:ss')]
    df = df.reset_index(drop=True)

    # convert date to human readable format (Thu 5/26 at 11:30 am)
    df['date'] = df['date'].apply(lambda x: arrow.get(x).format('ddd M/D h:mm a'))

    # export to json (convert escaped unicode to utf-8 encoding first)
    data = json.loads(df.to_json(orient='records', force_ascii=False))
    with open(json_fn, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def export_to_file(response, type: str='json', exclusions: str='') -> None:
    """
    Export to CSV or JSON
    """

    if exclusions != '':
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

        # TODO: don't wipe file with existing entries -- just remove duplicate key/value pairs
        # * cf."[{ "name": "SheCodesOKC", "date": "Tue 2/28 4:30 pm"," ... }]" -> "[]" (empty list)
        # ! Only happens locally; doesn't happen on server
        # ! Could be related to timestamp/ttl and/or removing duplicates logic
        # write json to file
        # if file exists, is less than n minutes old, append to file
        if (
            Path(json_fn).exists()
            and (arrow.now() - arrow.get(os.path.getmtime(json_fn))).seconds < ttl
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
    # refresh_token = tokens['refresh_token']

    # exclude keywords in event name and title (will miss events with keyword in description)
    exclusions = ['36\u00b0N', 'Tulsa', 'Nerdy Girls', 'Bitcoin']

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
            print(f'{Fore.GREEN}{info:<10}{Fore.RESET}No upcoming events for {url} found')
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

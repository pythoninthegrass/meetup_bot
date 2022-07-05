#!/usr/bin/env python3

import json
# import logging
import os
import pandas as pd
from decouple import config
from icecream import ic
# from markdown import markdown
from pathlib import Path
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# logging.basicConfig(level=logging.DEBUG)

# verbose icecream
ic.configureOutput(includeContext=True)

# pandas don't truncate output
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

# env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()
# format = 'json'
csv_fn = Path('raw/output.csv')
json_fn = Path('raw/output.json')
groups_csv = Path('raw/groups.csv')

# creds
if env.exists():
    USER_TOKEN = config('USER_TOKEN')
    BOT_USER_TOKEN = config('BOT_USER_TOKEN')
    SLACK_WEBHOOK = config('SLACK_WEBHOOK')
    SIGNING_SECRET = config('SIGNING_SECRET')
    ENDPOINT = config('ENDPOINT')
    CHANNEL = config('CHANNEL')
else:
    USER_TOKEN = os.getenv('USER_TOKEN')
    BOT_USER_TOKEN = os.getenv('BOT_USER_TOKEN')
    SLACK_WEBHOOK = os.getenv('SLACK_WEBHOOK')
    SIGNING_SECRET = os.getenv('SIGNING_SECRET')
    ENDPOINT = os.getenv('ENDPOINT')
    CHANNEL = os.getenv('CHANNEL')

# python sdk
client = WebClient(token=USER_TOKEN)

# read manually entered 'raw/channels.csv'
chan = pd.read_csv('raw/channels.csv')

# locate id from `CHANNEL` name
channel_id = chan[chan['name'] == CHANNEL]['id'].values[0]


def fmt_json(filename):
    # read json file
    data = json.load(open(filename))

    # create dataframe
    df = pd.DataFrame(data)

    # add column: 'message' with date, name, title, eventUrl
    df['message'] = df.apply(lambda x: f'• {x["date"]} *{x["name"]}* <{x["eventUrl"]}|{x["title"]}> ', axis=1)

    # convert message column to list of strings (avoids alignment shenanigans)
    msg = df['message'].tolist()

    return msg


def send_message(message):
    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text="",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                }
            ]
        )
    except SlackApiError as e:
        assert e.response["error"]

    return response


# TODO: transform json response vs. file
def main():
    # open json file and convert to list of strings
    msg = fmt_json(json_fn)

    # send message as one concatenated string
    send_message('\n'.join(msg))


if __name__ == '__main__':
    main()

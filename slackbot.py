#!/usr/bin/env python3

import arrow
import json
# import logging
import os
import pandas as pd
# import redis
import sys
from decouple import config
from gen_token import redis_connect
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
csv_fn = Path('raw/output.csv')
json_fn = Path('raw/output.json')
groups_csv = Path('raw/groups.csv')
TZ = config('TZ', default='America/Chicago')
local = arrow.now().to(TZ)

# creds
if env.exists():
    USER_TOKEN = config('USER_TOKEN')
    BOT_USER_TOKEN = config('BOT_USER_TOKEN')
    SLACK_WEBHOOK = config('SLACK_WEBHOOK')
    CHANNEL = config('CHANNEL')
    REDIS_PASS = config('REDIS_PASS')
    TTL = config('TTL', default=3600, cast=int)
    HOST = config('HOST', default='localhost')
else:
    USER_TOKEN = os.getenv('USER_TOKEN')
    BOT_USER_TOKEN = os.getenv('BOT_USER_TOKEN')
    SLACK_WEBHOOK = os.getenv('SLACK_WEBHOOK')
    CHANNEL = os.getenv('CHANNEL')
    REDIS_PASS = os.getenv('REDIS_PASS')
    TTL = os.getenv('TTL', default=3600)
    HOST = os.getenv('HOST', default='localhost')


# override host env var if system is macos
if sys.platform == 'darwin':
    HOST = 'localhost'

# python sdk
client = WebClient(token=BOT_USER_TOKEN)

# read manually entered 'raw/channels.csv'
chan = pd.read_csv('raw/channels.csv')

# locate id from `CHANNEL` name
channel_id = chan[chan['name'] == CHANNEL]['id'].values[0]

# init redis
r = redis_connect()


def log_post_status(time, key, ex=None):
    """
    Insert timestamp of Slack post into Redis
    """
    # insert timestamp into redis
    return r.ts(key, time, ex=ex)


def get_post_status(key):
    """
    Get timestamp of Slack post from Redis
    """
    return r.ts(key)


def fmt_json(filename):
    # read json file
    data = json.load(open(filename))

    # create dataframe
    df = pd.DataFrame(data)

    # add column: 'message' with date, name, title, eventUrl
    df['message'] = df.apply(
        lambda x: f'• {x["date"]} *{x["name"]}* <{x["eventUrl"]}|{x["title"]}> ',
        axis=1
    )

    # convert message column to list of strings (avoids alignment shenanigans)
    msg = df['message'].tolist()

    return msg


def send_message(message):
    """
    Send formatted Slack messages to a channel.

    NOTE: This function won't work with DMs or private channels.
    """
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
        return response
    except SlackApiError as e:
        assert e.response["ok"] is False
        assert e.response["error"]
        print(f"Got an error: {e.response['error']}")


# TODO: transform json response vs. file
def main():
    # open json file and convert to list of strings
    msg = fmt_json(json_fn)

    # send message as one concatenated string
    send_message('\n'.join(msg))


if __name__ == '__main__':
    main()
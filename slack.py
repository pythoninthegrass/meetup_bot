#!/usr/bin/env python3

import json
# import logging
import os
import pandas as pd
# import requests
# import time
from decouple import config
from icecream import ic
# from markdown import markdown
from pathlib import Path
# from slack_bolt import App
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
    PORT = config('BOLT_PORT', default=3001, cast=int)
else:
    USER_TOKEN = os.getenv('USER_TOKEN')
    BOT_USER_TOKEN = os.getenv('BOT_USER_TOKEN')
    SLACK_WEBHOOK = os.getenv('SLACK_WEBHOOK')
    SIGNING_SECRET = os.getenv('SIGNING_SECRET')
    ENDPOINT = os.getenv('ENDPOINT')
    CHANNEL = os.getenv('CHANNEL')
    PORT = int(os.getenv('BOLT_PORT'))

# python sdk
client = WebClient(token=USER_TOKEN)

# read manually entered 'raw/channels.csv'
chan = pd.read_csv('raw/channels.csv')

# locate id from `CHANNEL` name
channel_id = chan[chan['name'] == CHANNEL]['id'].values[0]

# convo_list = client.conversations_list()
# # pandas read list of dictionaries
# df = pd.DataFrame(convo_list["channels"])
# # export response to json
# df.to_json('raw/channels.json', orient='records')


def fmt_json(filename):
    # read json file
    data = json.load(open(filename))

    # create dataframe
    df = pd.DataFrame(data)

    # add column: 'message' with date, name, title, eventUrl
    df['message'] = df.apply(lambda x: f'• {x["date"]} *{x["name"]}* <{x["eventUrl"]}|{x["title"]}> ', axis=1)

    # convert message to a single string
    # msg = df['message'].to_string(index=False)

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


def main():
    # msg = \
    # """
    # <https://github.com/leachim6/hello-world/wiki/|Hello world!> :python2: :point_right: :joy:
    # """

    # # read md file
    # md = Path('resources/MESSAGE.md')
    # with open(md, 'r') as f:
    #     msg = f.read()

    # # https://api.slack.com/reference/surfaces/formatting#block-formatting
    # # replace '*' with '•' in `msg`
    # msg = msg.replace('*', '•')

    msg = fmt_json(json_fn)

    # send message as one concatenated string
    send_message('\n'.join(msg))


if __name__ == '__main__':
    main()


# REQUESTS

# webhook_url = SLACK_WEBHOOK
# base_url = "https://slack.com/api/"
# endpoint = base_url + ENDPOINT

# def send_message(message):
#     """
#     Send a message to Slack
#     """
#     # curl -X POST -H 'Content-type: application/json' --data '{"text":"Hello, World!"}' $SLACK_WEB_HOOK
#     payload = {
#         "channel": CHANNEL,
#         "text": message
#     }
#     response = requests.post(
#         webhook_url,
#         data=json.dumps(payload),
#         headers={'Content-Type': 'application/json'}
#     )
#     return response


# send_message()


# BOLT

# # Initializes your app with your bot token and signing secret
# app = App(
#     token=BOT_USER_TOKEN,
#     signing_secret=SIGNING_SECRET
# )


# # Listens to incoming messages that contain "hello"
# @app.message(":python2:")
# def message_hello(message, say):
#     """say() sends a message to the channel where the event was triggered"""
#     say(
#         blocks=[
#             {
#                 "type": "section",
#                 "text": {"type": "mrkdwn", "text": f"Hey there <@{message['user']}>!"},
#                 "accessory": {
#                     "type": "button",
#                     "text": {"type": "plain_text", "text": "Click Me"},
#                     "action_id": "button_click"
#                 }
#             }
#         ],
#         text=f"Bienvenue <@{message['user']}>!"
#     )


# if __name__ == "__main__":
#     app.start(port=PORT)

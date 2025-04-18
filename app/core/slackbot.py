#!/usr/bin/env python3

import pandas as pd
import time
from app.core.meetup_query import get_all_events
from app.utils.schedule import should_post_to_slack
from config import *
from decouple import config
from icecream import ic
from pathlib import Path
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# verbose icecream
ic.configureOutput(includeContext=True)

# env
home = Path.home()
cwd = Path.cwd()
csv_fn = config('CSV_FN', default='raw/output.csv')
json_fn = config('JSON_FN', default='raw/output.json')
groups_csv = Path('groups.csv')
loc_time = CURRENT_TIME_LOCAL
bypass_schedule = config('OVERRIDE', default=False, cast=bool)
time.tzset()

# creds
USER_TOKEN = config('USER_TOKEN')
BOT_USER_TOKEN = config('BOT_USER_TOKEN')
SLACK_WEBHOOK = config('SLACK_WEBHOOK')
CHANNEL = config('CHANNEL', default='testingchannel')
TTL = config('TTL', default=3600, cast=int)
HOST = config('HOST', default='localhost')

# strip double quotes from env strings (local image)
CHANNEL = CHANNEL.strip('"')


def load_channels():
    # read channel
    chan = pd.read_csv('channels.csv', header=0)

    # create dict of channels
    chan_dict = {}

    # loop through channels and find id
    for name, id in zip(chan['name'], chan['id'], strict=False):
        chan_dict[name] = id

    # channel name and id
    channel_name = CHANNEL
    channel_id = chan_dict[CHANNEL]

    # hard-coded second channel
    hard_chan = ''

    # add hard-coded channel
    if hard_chan != '':
        hard_id = chan_dict[hard_chan]
        channels = {
            channel_name: channel_id,
            hard_chan: hard_id
        }
    else:
        channels = {
            channel_name: channel_id
        }

    return channels


# python sdk
client = WebClient(token=BOT_USER_TOKEN)


def send_message(message, channel_id):
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
    except Exception as e:
        print(f"Got an error: {str(e)}")
        return None


def main(override=bypass_schedule):
    """
    Main function to post events to Slack channels
    Only posts if the schedule allows it or if override is True
    """
    # Check if we should post based on schedule
    schedule_check = should_post_to_slack(override)
    if not schedule_check["should_post"]:
        reason = schedule_check.get("reason", "Not scheduled for posting at this time")
        print(f"Skipping Slack post: {reason}")
        return []

    # load channels
    channels = load_channels()

    # Get events
    events = get_all_events()

    # Format messages
    messages = []
    for event in events:
        message = f'• {event["date"]} *{event["name"]}* <{event["eventUrl"]}|{event["title"]}> '
        messages.append(message)

    # Only send messages if we have events
    if messages:
        # send message as one concatenated string
        for _, channel_id in channels.items():
            send_message('\n'.join(messages), channel_id)
        print(f"Posted {len(messages)} events to {len(channels)} channels")
    else:
        print("No events to post")

    return ic(messages)


if __name__ == '__main__':
    main()

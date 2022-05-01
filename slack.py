#!/usr/bin/env python3

import json
import os
import requests
from decouple import config
from pathlib import Path

# env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()

# creds
if env.exists():
    BOT_USER_TOKEN = config('BOT_USER_TOKEN')
    SLACK_WEBHOOK = config('SLACK_WEBHOOK')
    CHANNEL = config('CHANNEL')
else:
    BOT_USER_TOKEN = os.getenv('BOT_USER_TOKEN')
    SLACK_WEBHOOK = os.getenv('SLACK_WEBHOOK')
    CHANNEL = os.getenv('CHANNEL')

webhook_url = SLACK_WEBHOOK


def send_message(message):
    """
    Send a message to Slack
    """
    # curl -X POST -H 'Content-type: application/json' --data '{"text":"Hello, World!"}' $SLACK_WEB_HOOK
    payload = {
        "channel": CHANNEL,
        "text": message
    }
    response = requests.post(
        webhook_url,
        data=json.dumps(payload),
        headers={'Content-Type': 'application/json'}
    )
    return response


# send_message()

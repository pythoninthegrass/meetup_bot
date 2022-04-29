#!/usr/bin/env python3

import os
import requests
import requests_cache
import tqdm
from decouple import config
from knockknock import slack_sender
from pathlib import Path

# env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()

# verbose icecream
# ic.configureOutput(includeContext=True)

requests_cache.install_cache("api_cache")

# creds
if env.exists():
    BOT_USER_TOKEN = config('BOT_USER_TOKEN')
    SLACK_WEBHOOK = config('SLACK_WEBHOOK')
else:
    BOT_USER_TOKEN = os.getenv('BOT_USER_TOKEN')
    SLACK_WEBHOOK = os.getenv('SLACK_WEBHOOK')

webhook_url = SLACK_WEBHOOK


def isprime(n):
    if n == 2:
        return True
    if n < 2 or n % 2 == 0:
        return False
    for i in range(3, int(n**0.5)+1, 2):
        if n % i == 0:
            return False
    return True


@slack_sender(webhook_url = webhook_url, channel="knockknock")
def get_prime_numbers(max_value):

    final_prime_numbers = []

    for num in tqdm(range(max_value)):

      if(isprime(num)):
        final_prime_numbers.append(num)

    return final_prime_numbers

 # Run the function with a value of 20
get_prime_numbers(20)

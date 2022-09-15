#!/usr/bin/env python3

import arrow
import atexit
import os
import requests
import sys
import time
from apscheduler.schedulers.background import BackgroundScheduler
from decouple import config
from pathlib import Path
from urllib.parse import urlencode

env = Path('.env')

# creds
if env.exists():
    HOST = config('HOST')
    PORT = config('PORT', default=3000, cast=int)
    DB_USER = config('DB_USER')
    DB_PASS = config('DB_PASS')
else:
    HOST = os.getenv('HOST')
    PORT = int(os.getenv('PORT', default=3000))
    DB_USER = os.getenv('DB_USER')
    DB_PASS = os.getenv('DB_PASS')

# scheduler
TZ = config('TZ', default='America/Chicago')
loc_time = arrow.now().to(TZ)
time.tzset()
sched = BackgroundScheduler()
sched.configure(timezone=TZ)


@sched.scheduled_job('interval', minutes=55, id='gen_token')
def get_token():
    """Get token from db"""

    url = f"http://{HOST}:{PORT}/token"

    payload = f"username={DB_USER}&password={DB_PASS}"

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    res = requests.request("POST", url, headers=headers, data=payload)

    raw = res.json()

    return raw['access_token']


# @sched.scheduled_job(trigger='cron', hour='9,17,20,23', id='post_slack')  # 9am, 5pm, 8pm, 11pm
# @sched.scheduled_job(trigger='cron', hour='*', id='post_slack')           # every hour
@sched.scheduled_job(trigger='cron', minute=30, id='post_slack')            # every 30 minutes
def post_to_slack():
    """Post to Slack"""

    access_token = get_token()

    url = f"http://{HOST}:{PORT}/api/slack"

    payload = urlencode({
        'location': 'Oklahoma City',
        'exclusions': 'Tulsa'
    })

    headers = {
        'Authorization': f'Bearer {access_token}',
        'accept': 'application/json'
    }

    res = requests.request("POST", url, headers=headers, data=payload)

    return res.json()


def main():
    """Main function"""

    import uvicorn

    sched.start()
    atexit.register(lambda: sched.shutdown())

    try:
        uvicorn.run("main:app", host="0.0.0.0", port=3001, reload=True)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(e)
        sys.exit(1)


if __name__ == '__main__':
    main()

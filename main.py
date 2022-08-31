#!/usr/bin/env python3

import os
import pandas as pd
import redis
import sys
from decouple import config
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from gen_token import main as gen_token
from gen_token import redis_connect as redis_connect
from gen_token import start_docker as start_docker
# from icecream import ic
from meetup_query import *
from pathlib import Path
from python_on_whales import docker
from slackbot import *

# verbose icecream
# ic.configureOutput(includeContext=True)

# pandas don't truncate output
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

# logging.basicConfig(level=logging.DEBUG)
# requests_cache.install_cache("api_cache", expire_after=3600)

# verbose icecream
# ic.configureOutput(includeContext=True)

# env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()
csv_fn = Path('raw/output.csv')
json_fn = Path('raw/output.json')
env =  Path('.env')

# creds
if env.exists():
    REDIS_URL: config('REDIS_URL', default=None)
    REDIS_PASS = config('REDIS_PASS')
    TTL = config('TTL', default=3600, cast=int)
    HOST = config('HOST', default='redis')
    PORT = config('PORT', default=3000, cast=int)
else:
    REDIS_URL = os.getenv('REDIS_URL')
    REDIS_PASS = os.getenv('REDIS_PASS')
    TTL = os.getenv('TTL', default=3600)
    HOST = os.getenv('HOST', default='redis')
    PORT = os.getenv('PORT', default=3000)


"""
FastAPI app
"""

# main web app
app = FastAPI(title="meetup_bot API", openapi_url="/meetup_bot.json")

# add `/api` route in front of all other endpoints
api_router = APIRouter(prefix="/api")

# CORS
origins = [
    "http://localhost",
    "http://localhost:" + str(PORT),
    "http://127.0.0.1",
    "http://127.0.0.1:" + str(PORT),
    "http://0.0.0.0",
    "http://0.0.0.0:" + str(PORT),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event('startup')
def startup_event():
    """
    Run startup event
    """

    # override host env var if system is macos
    if HOST == 'localhost' or sys.platform == 'darwin':
        # start containers (only build if images aren't present)
        start_docker(yml_file='docker-compose.yml')

    # make handshake with redis
    redis_connect()


@app.get("/")
async def root():
    return {"message": "Hello World"}


# TODO: QA hard-coded token pos arg
@api_router.get("/token")
def generate_token(hard_token: str = None):
    """
    Get auth token

    Args:
        hard_token (str): hard-coded token
    """

    global token

    if hard_token:
        token = hard_token
    else:
        tokens = gen_token()
        token = tokens[0]

    return token


# TODO: decouple export from formatted response
@api_router.get("/events")
def get_events(
    location: str = "Oklahoma City",
    exclusions: str = "Tulsa"):
    """
    Query upcoming Meetup events
    """

    # if exclusions, add to list of exclusions
    if exclusions:
        exclusions = exclusions.split(",")
    else:
        exclusions = []

    token = generate_token()
    response = send_request(token, query, vars)

    export_to_file(response, format, exclusions=exclusions)                  # csv/json

    # third-party query
    output = []
    for url in url_vars:
        response = send_request(token, url_query, f'{{"urlname": "{url}"}}')
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
        return pd.read_csv(csv_fn)
    elif format == 'json':
        sort_json(json_fn)
        return pd.read_json(json_fn)


# TODO: see get_events TODO ^^
# @api_router.post("/export")
# def export_events(format: str = "json"):
#     """
#     Export Meetup events to CSV or JSON
#     """

#     # validate format
#     format = format.lower()
#     if format not in ["json", "csv"]:
#         raise HTTPException(status_code=400, detail="Invalid format. Must be either 'json' or 'csv'")

#     # token = generate_token()
#     # response = send_request(token, query, vars)

#     response = get_events()
#     export_to_file(response, format)

#      # cleanup output file
#     if format == 'csv':
#         return sort_csv(csv_fn)
#     elif format == 'json':
#         return sort_json(json_fn)


@api_router.post("/slack")
def post_slack(
    location: str = "Oklahoma City",
    exclusions: str = "Tulsa"):
    """
    Post to slack

    Calls main function to post formatted message to predefined channel
    """

    get_events(location, exclusions)

    msg = fmt_json(json_fn)

    send_message('\n'.join(msg))

    return ic(msg)


app.include_router(api_router)


# TODO: uvicorn server time to either local or utc
def main():
    """
    Run app
    """

    # Use this for debugging purposes only
    import uvicorn

    try:
        uvicorn.run("main:app", host="0.0.0.0", port=PORT, limit_max_requests=10000, log_level="debug", reload=True)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(e)
    finally:
        if sys.platform == 'darwin':
            print("[INFO] Stopping docker containers")
            docker.compose.stop(
                services=[
                    'redis',
                    'redisinsight',
                    'meetupbot',
                ],
            )
            print("[INFO] Successfully stopped containers. Exiting...")
        exit()


if __name__ == "__main__":
    main()

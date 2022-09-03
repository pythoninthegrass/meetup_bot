#!/usr/bin/env python3

import os
import pandas as pd
import sys
import time
from decouple import config
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sign_jwt import main as gen_token
# from icecream import ic
from meetup_query import *
from pathlib import Path
from pony.orm import *
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
    TTL = config('TTL', default=3600, cast=int)
    HOST = config('HOST')
    PORT = config('PORT', default=3000, cast=int)
else:
    TTL = os.getenv('TTL', default=3600)
    HOST = os.getenv('HOST')
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

    # TODO: background tasks: generate access and refresh tokens every 55 minutes(fastapi/rocketry); post to slack every 24 hours

    # generate access and refresh tokens
    # tokens = gen_token()
    # access_token = tokens['access_token']
    # refresh_token = tokens['refresh_token']
    access_token = ''
    refresh_token = ''
    expiration = int(time.time()) + TTL

    # init db
    db = Database()

    # in-memory sqlite db
    db.bind(provider='sqlite', filename=':memory:')


    class Token(db.Entity):
        access_token = Required(str)
        refresh_token = Required(str)
        expiration = Optional(str)


    db.generate_mapping(create_tables=True)


    # TODO: QA expiration cast
    @db_session
    def add_tokens(access_token: str = None, refresh_token: str = None, expiration: str = None):
        Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expiration=expiration
        )


    @db_session
    def get_token(access_token: str = None, refresh_token: str = None, expiration: str = None):
        access_token = Token.get(access_token='access_token')
        refresh_token = Token.get(refresh_token='refresh_token')
        expiration = Token.get(expiration='expiration')

        return access_token, refresh_token, expiration


    # add tokens to db
    add_tokens(access_token, refresh_token, expiration)

    # get tokens from db
    get_token('access_token', 'refresh_token')

    return access_token, refresh_token


@app.get("/")
async def root():
    return {"message": "Hello World"}


# TODO: QA hard-coded token pos arg
@api_router.get("/token")
def generate_token(access_token: str = None,
                    refresh_token: str = None):
    """
    Get access and refresh tokens

    Args:
        access_token (str): hard-coded access_token
        refresh_token (str): hard-coded refresh_token
    """

    if access_token and refresh_token:
        access_token = access_token
        refresh_token = refresh_token
    else:
        tokens = gen_token()
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']

    return access_token, refresh_token


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

    access_token, refresh_token = generate_token()
    response = send_request(access_token, query, vars)

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
        return pd.read_csv(csv_fn)
    elif format == 'json':
        sort_json(json_fn)
        return pd.read_json(json_fn)


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
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

# import arrow
import asyncio
from urllib import response
# import aiohttp
# import aiofile
import json
# import nest_asyncio
import os
import pandas as pd
# import requests
# import requests_cache
import time
from decouple import config
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import FileResponse, StreamingResponse
from icecream import ic
from pathlib import Path
# from requests_cache import CachedSession
# from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError
# import gen_token
# import meetup_query
# import slackbot
from gen_token import main as gen_token
from meetup_query import *
from slackbot import main as send_message

# verbose icecream
ic.configureOutput(includeContext=True)

# pandas don't truncate output
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

# logging.basicConfig(level=logging.DEBUG)
# requests_cache.install_cache("api_cache", expire_after=3600)

## env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()

# verbose icecream
ic.configureOutput(includeContext=True)

# env file
env =  Path('.env')

# creds
if env.exists():
    PORT = config('PORT', default=3000, cast=int)
else:
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

# sync function call to generate token
tokens = gen_token()
token = tokens[0]


@app.on_event('startup')
async def startup_event():
    """
    Run startup event
    """

    global response
    response = send_request(token, query, vars)

    return response


@app.get("/")
async def root():
    return {"message": "Hello World"}


# TODO: fix exclusions blocking response (empty df)
@api_router.get("/events")
def get_events(location: str = "Oklahoma City", exclusions: str = "Tulsa"):
    """
    Query upcoming Meetup events
    """

    # wait for async function to complete
    try:
        asyncio.get_event_loop().run_until_complete(startup_event())
    except RuntimeError as e:
        print(e)
        pass

    # first-party query
    res = format_response(response, location=location, exclusions=exclusions)

    # add to df
    df = pd.DataFrame(res)

    # third-party query
    for url in url_vars:
        res = send_request(token, url_query, f'{{"urlname": "{url}"}}')
        # append to output dict if the response is not empty
        if len(format_response(res, location=location, exclusions=exclusions)) > 0:
            df = pd.concat([df, pd.DataFrame(format_response(res, location=location, exclusions=exclusions))])
        else:
            print(f'[INFO] No upcoming events for {url} found')

    # clean up duplicates
    df = df.drop_duplicates()

    # sort
    df = sort_response(df)

    return df


@api_router.get("/export")
def export_events(format: str = "json", exclusions: str = ""):
    """
    Export Meetup events to CSV or JSON
    """

    # exclude keywords in event name and title (will miss events with keyword in description)
    exclusions = ['36\u00b0N', 'Tulsa']

    # validate format
    format = format.lower()
    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Invalid format. Must be either 'json' or 'csv'")

    return export_to_file(response, format, exclusions=exclusions)


@api_router.get("/slack")
def post_slack(message):
    """
    Post to slack
    """

    return send_message(message)


app.include_router(api_router)


def main():
    """
    Run app
    """

    # Use this for debugging purposes only
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, limit_max_requests=10000, log_level="debug", reload=True)


# TODO: shutdown docker containers on exit
if __name__ == "__main__":
    main()

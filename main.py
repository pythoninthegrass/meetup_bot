#!/usr/bin/env python3

# import arrow
# import asyncio
from urllib import response
# import aiohttp
# import aiofile
import json
import os
import pandas as pd
import requests
import requests_cache
from decouple import config
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from gen_token import main as gen_token
from meetup_query import send_request, format_response, export_to_file
from icecream import ic
from pathlib import Path
# from requests_cache import CachedSession
from slack import send_message
# from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError

# verbose icecream
ic.configureOutput(includeContext=True)

# show all columns
pd.set_option('display.max_columns', None)

# logging.basicConfig(level=logging.DEBUG)
requests_cache.install_cache("api_cache", expire_after=3600)

## env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()

## verbose icecream
# ic.configureOutput(includeContext=True)

# env file
env =  Path('.env')

# creds
if env.exists():
    PORT = config('PORT', default=3000, cast=int)
else:
    PORT = os.getenv('PORT', default=3000, cast=int)


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
    tokens = gen_token()
    global token
    token = tokens[0]

    global response
    response = send_request(token)

    # global json_response
    # json_response = json.loads(response)

    return token, response


@app.get("/")
async def root():
    return {"message": "Hello World"}


@api_router.get("/events")
def get_events(location: str = "Oklahoma City"):
    """
    Query upcoming Meetup events
    """

    # if child script raises error, throw 404
    try:
        res = format_response(response, location)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f'No data for {location} found')


@api_router.get("/export")
def export_events(format: str = "json"):
    """
    Export Meetup events to CSV or JSON
    """

    # validate format
    format = format.lower()
    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Invalid format. Must be either 'json' or 'csv'")

    return export_to_file(response, format)


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


if __name__ == "__main__":
    main()

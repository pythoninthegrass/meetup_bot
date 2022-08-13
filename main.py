#!/usr/bin/env python3

import os
import pandas as pd
import sys
from decouple import config
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from gen_token import main as gen_token
from meetup_query import *
from slackbot import main as send_message
# from icecream import ic
from pathlib import Path
from python_on_whales import docker

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
def startup_event():
    """
    Run startup event
    """

    global response
    response = send_request(token, query, vars)

    return response


@app.get("/")
async def root():
    return {"message": "Hello World"}


# TODO: better output than `null` for each endpoint
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

    return format_response(response, location=location, exclusions=exclusions)


# TODO: override path in dev and/or use filestream (cf. news aggregator project)
@api_router.post("/export")
def export_events(format: str = "json"):
    """
    Export Meetup events to CSV or JSON
    """

    # validate format
    format = format.lower()
    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Invalid format. Must be either 'json' or 'csv'")

    export_to_file(response, format)

     # cleanup output file
    if format == 'csv':
        return sort_csv(csv_fn)
    elif format == 'json':
        return sort_json(json_fn)


@api_router.post("/slack")
def post_slack():
    """
    Post to slack

    Calls main function to post formatted message to predefined channel
    """

    return send_message()


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

#!/usr/bin/env python3

# import arrow
import asyncio
import aiohttp
import aiofile
# import io
# import logging
import os
import pandas as pd
# import re
import requests
import requests_cache
from decouple import config
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from icecream import ic
# from <local.py_module> import *
from pathlib import Path
# from prettytable import PrettyTable
# from requests_cache import CachedSession
from slack import *
# from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError

## verbose icecream
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
app = FastAPI(title="slackathon API", openapi_url="/slackathon.json")

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

@app.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.get("/emoji")
def get_emoji_list(url=endpoint):
    """
    Get the list of emoji from the Slack API.

    The two URL methods are:\n
    https://slack.com/api/emoji.list\n
    https://slack.com/api/admin.emoji.list
    """

    if url == endpoint:
        headers = {
            'Authorization': f'Bearer {BOT_USER_TOKEN}',
        }

    response = requests.get(url, headers=headers)

    return response.json()


app.include_router(api_router)


if __name__ == "__main__":
    # Use this for debugging purposes only
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, limit_max_requests=10000, log_level="debug", reload=True)

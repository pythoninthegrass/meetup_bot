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


@api_router.get("/export/csv")
def export_emoji_list(url=endpoint):
    """
    Export the list of emoji to a CSV file.

    The two URL methods are:\n
    https://slack.com/api/emoji.list\n
    https://slack.com/api/admin.emoji.list
    """

    # read json from response
    df = pd.DataFrame.from_dict(get_emoji_list(url))

    # drop ok, cache_ts columns
    df = df.drop(columns=['ok', 'cache_ts'])

    # name first column as 'name'
    df['name'] = df.index.values

    # reset index to count from 0
    df = df.reset_index(drop=True)

    # move name to first column
    first_column = df.pop('name')
    df.insert(0, 'name', first_column)

    # rename emoji to url column
    df = df.rename(columns={'emoji': 'url'})

    # csv file
    file_name = "response.csv"

    # write to csv
    df.to_csv(file_name, index=False)

    # return file
    return FileResponse(file_name, media_type="text/csv")


@api_router.get("/export/images")
def download_emoji_images(url=endpoint):
    """
    Download the list of emoji images to a directory.

    The two URL methods are:\n
    https://slack.com/api/emoji.list\n
    https://slack.com/api/admin.emoji.list
    """

    # if response.csv exists, skip url call
    if Path(f"{cwd}/response.csv").exists():
        # skip header
        df = pd.read_csv(f"{cwd}/response.csv", skip_blank_lines=True)
    else:
        # read json from response
        df = pd.DataFrame.from_dict(get_emoji_list(url))

    # asynchronously download emoji with n max concurrent requests
    sema = asyncio.BoundedSemaphore(10000)
    async def download_image(url, file_path):
        async with sema:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.read()
                    async with aiofile.AIOFile(file_path, "wb") as f:
                        await f.write(data)

    # length of df
    total_emoji = df.shape[0]
    ic(f"Total emoji: {total_emoji}")

    # TODO: extract int from df `url 240 dtype: int64`
    # count emoji column rows that contain value "alias:"
    aliases = df.iloc[:, 1:].apply(lambda x: x.str.contains("alias:").sum())
    ic(f"Total aliases: {aliases}")

    # net emoji
    net_emoji = total_emoji - aliases
    ic(f"Net emoji: {net_emoji}")

    # number of existing emoji files
    existing_emoji = len(os.listdir(f"{cwd}/images"))
    ic(f"Existing emoji: {existing_emoji}")

    # delta
    delta = net_emoji - existing_emoji
    ic(f"Outstanding emoji: {delta}")

    # loop through 'url' column in df
    for name, emoji in zip(df['name'], df['url']):
        if not emoji.startswith("https"):
            continue
        # ic(name, emoji)

        # get suffix of image (png, gif, etc)
        suffix = emoji.split(".")[-1]

        # rename file
        file_name = f"{cwd}/images/{name}.{suffix}"

        # check if file exists and skip if it does
        if Path(file_name).exists():
            # ic(f"{file_name} already exists")
            continue

        # download image
        print(f"Downloading image: {emoji}")
        asyncio.run(download_image(emoji, file_name))

    return {"message": f"Downloaded {delta} images"}


app.include_router(api_router)


if __name__ == "__main__":
    # Use this for debugging purposes only
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, limit_max_requests=10000, log_level="debug", reload=True)

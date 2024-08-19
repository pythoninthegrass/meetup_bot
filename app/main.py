#!/usr/bin/env python3

import arrow
import pandas as pd
import sys
import time
from colorama import Fore
from datetime import datetime, timedelta
from decouple import config
from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from icecream import ic
from jose import JWTError, jwt
from meetup_query import *
from passlib.context import CryptContext
from pathlib import Path
from pony.orm import Database, Required, Optional, PrimaryKey, Set, db_session
from pydantic import BaseModel
from schedule import get_schedule, snooze_schedule, check_and_revert_snooze
from sign_jwt import main as gen_token
from slackbot import *
from typing import List, Union

# verbose icecream
ic.configureOutput(includeContext=True)

# logging prefixes
info = "INFO:"
error = "ERROR:"
warning = "WARNING:"

# env
home = Path.home()
cwd = Path.cwd()
csv_fn = config("CSV_FN", default="raw/output.csv")
json_fn = config("JSON_FN", default="raw/output.json")
tz = config("TZ", default="America/Chicago")

# time
loc_time = arrow.now().to(tz)
time.tzset()

# pandas don't truncate output
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option('display.max_colwidth', None)

# index
templates = Jinja2Templates(directory=Path("resources/templates"))

# creds
TTL = config("TTL", default=3600, cast=int)
HOST = config("HOST")
PORT = config("PORT", default=3000, cast=int)
SECRET_KEY = config("SECRET_KEY")
ALGORITHM = config("ALGORITHM", default="HS256")
TOKEN_EXPIRE = config("TOKEN_EXPIRE", default=30, cast=int)
DB_NAME = config("DB_NAME")
DB_USER = config("DB_USER")
DB_PASS = config("DB_PASS")
DB_HOST = config("DB_HOST")
DB_PORT = config("DB_PORT", default=5432, cast=int)


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


"""
Database
"""

# init db
db = Database()


# user model
class UserInfo(db.Entity):
   username = Required(str, unique=True)
   # password = Required(str)
   hashed_password = Required(str)
   email = Optional(str)


# sqlite db
# db.bind(provider='sqlite', filename=DB_NAME, create_db=True)      # local db
# db.bind(provider='sqlite', filename=':memory:')                   # in-memory db

# strip double quotes from string
DB_PASS = DB_PASS.strip('"')                                        # local image

# postgres db
db.bind(provider='postgres',
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        database=DB_NAME,
        port=DB_PORT,
        sslmode='require'
)

# generate mapping
db.generate_mapping(create_tables=True)


"""
Authentication
"""

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    """Validate plaintext password against hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Return hashed password"""
    return pwd_context.hash(password)


def get_user(username: str):
    with db_session:
        user = UserInfo.get(username=username)
        if user:
            return UserInDB(username=user.username, hashed_password=user.hashed_password)


def authenticate_user(username: str, password: str):
    """Authenticate user"""
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False

    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


# TODO: store user session in cookie
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Get current active user"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")

    return current_user


@app.post("/token", response_model=Token)
async def login_for_oauth_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login for oauth access token"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    oauth_token_expires = timedelta(minutes=TOKEN_EXPIRE)
    oauth_token = create_access_token(
        data={"sub": user.username}, expires_delta=oauth_token_expires
    )

    return {"access_token": oauth_token, "token_type": "bearer"}


"""
Login
"""


def load_user(username: str):
    with db_session:
        user = UserInfo.get(username=username)
        if user:
            return user
        else:
            raise HTTPException(status_code=404, detail="User not found")


"""
Startup
"""


# TODO: https://fastapi.tiangolo.com/advanced/events/
@app.on_event("startup")
def startup_event():
    """
    Run startup event
    """

    # create user
    with db_session:
        if not UserInfo.exists(username=DB_USER):
            hashed_password = get_password_hash(DB_PASS)
            UserInfo(username=DB_USER, hashed_password=hashed_password)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    with open(Path("resources/templates/login.html")) as f:
        return HTMLResponse(content=f.read(), status_code=200)


@app.post("/auth/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Redirect to "/docs" from index page if user successfully logs in with HTML form"""
    if load_user(username) and verify_password(password, load_user(username).hashed_password):
        return RedirectResponse(url="/docs", status_code=303)


# TODO: use refresh token to get new access token
@api_router.get("/token")
def generate_token(current_user: User = Depends(get_current_active_user)):
    """
    Get access and refresh tokens

    Args:
        access_token (str): hard-coded access_token
        refresh_token (str): hard-coded refresh_token
    """

    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    global access_token, refresh_token

    # generate access and refresh tokens
    try:
        tokens = gen_token()
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']
    except KeyError as e:
        print(f"{Fore.RED}{error:<10}{Fore.RESET}KeyError: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return access_token, refresh_token


# TODO: decouple export from formatted response
@api_router.get("/events")
def get_events(location: str = "Oklahoma City", exclusions: str = "Tulsa", current_user: User = Depends(get_current_active_user)):
    """
    Query upcoming Meetup events

    Args:
        location (str): location to search for events
        exclusions (str): location to exclude from search
    """

    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    access_token, refresh_token = generate_token()

    # default exclusions
    exclusion_list = ["36\u00b0N", "Nerdy Girls"]

    # if exclusions, add to list of exclusions
    if exclusions is not None:
        exclusions = exclusions.split(",")
        exclusion_list = exclusion_list + exclusions

    response = send_request(access_token, query, vars)

    export_to_file(response, format, exclusions=exclusion_list)

    # third-party query
    output = []
    for url in url_vars:
        response = send_request(access_token, url_query, f'{{"urlname": "{url}"}}')
        # append to output dict if the response is not empty
        if len(format_response(response, exclusions=exclusion_list)) > 0:
            output.append(response)
        else:
            print(f"{Fore.GREEN}{info:<10}{Fore.RESET}No upcoming events for {url} found")
    # loop through output and append to file
    for i in range(len(output)):
        export_to_file(output[i], format)

    # cleanup output file
    sort_json(json_fn)

    return pd.read_json(json_fn)


@api_router.get("/check-schedule")
def should_post_to_slack(auth: dict = Depends(ip_whitelist_or_auth), request: Request = None):
    """
    Check if it's time to post to Slack based on the schedule
    """
    current_time = arrow.now(tz)
    current_day = current_time.format("dddd")  # e.g., "Monday"

    with db_session:
        check_and_revert_snooze()  # Check and revert any expired snoozes
        schedule = get_schedule(current_day)
        if schedule and schedule.enabled:
            # Parse the schedule_time as a time, not a full date-time
            schedule_time = arrow.get(schedule.schedule_time, "HH:mm").replace(tzinfo=schedule.timezone)
            schedule_time_local = schedule_time.to(tz)

            # Is time within 5 minutes of scheduled time
            time_diff = abs(
                (current_time.hour * 60 + current_time.minute) - (schedule_time_local.hour * 60 + schedule_time_local.minute)
            )

            should_post = time_diff <= 5

            if request:
                # If it's a web request, return a JSON response
                return {
                    "should_post": should_post,
                    "current_time": current_time.isoformat(),
                    "schedule_time": schedule_time_local.isoformat(),
                    "time_diff_minutes": time_diff,
                }
            else:
                # If it's an internal call, return a boolean
                return should_post

    # If no schedule found or not enabled
    if request:
        return {"should_post": False, "reason": "No schedule found or not enabled"}
    else:
        return False


@api_router.post("/slack")
def post_slack(
    location: str = "Oklahoma City",
    exclusions: str = "Tulsa",
    channel_name: str = None,
    current_user: User = Depends(get_current_active_user),
    override: bool = False,
):
    """
    Post to slack

    Calls main function to post formatted message to predefined channel
    """

    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not should_post_to_slack() and not override:
        return {"message": "Not scheduled to post at this time"}

    get_events(location, exclusions=exclusions)

    # open json file and convert to list of strings
    msg = fmt_json(json_fn)

    # if channel_name is not None, post to channel as one concatenated string
    if channel_name is not None:
        # get channel id chan_dict key value pair
        channel_id = chan_dict[channel_name]
        # post to single channel
        send_message("\n".join(msg), channel_id)
    else:
        # post to all channels
        for name, id in channels.items():
            send_message('\n'.join(msg), id)

    return ic(msg)


# routes
app.include_router(api_router)


def main():
    """
    Run app
    """

    import uvicorn

    try:
        uvicorn.run("main:app",
                    host="0.0.0.0",
                    port=PORT,
                    limit_max_requests=10000,
                    log_level="warning",
                    reload=True)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()

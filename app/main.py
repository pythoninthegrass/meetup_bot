#!/usr/bin/env python3

import asyncio
import json
import pandas as pd
import sys
import time
from colorama import Fore
from config import *
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from decouple import config
from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from icecream import ic
from jose import JWTError, jwt
from math import ceil
from meetup_query import get_all_events
from passlib.context import CryptContext
from pathlib import Path
from pony.orm import Database, Optional, PrimaryKey, Required, Set, db_session
from pydantic import BaseModel
from schedule import check_and_revert_snooze, get_current_schedule_time, get_schedule, snooze_schedule
from sign_jwt import main as gen_token
from slackbot import *
from typing import Union

# verbose icecream
ic.configureOutput(includeContext=True)

# env
home = Path.home()
cwd = Path.cwd()
json_fn = config("JSON_FN", default="raw/output.json")
tz = config("TZ", default="America/Chicago")
bypass_schedule = config("OVERRIDE", default=False, cast=bool)

# time
current_time_local = arrow.now(tz)
current_time_utc = arrow.utcnow()
current_day = current_time_local.format("dddd")  # Monday, Tuesday, etc.
time.tzset()

# pandas don't truncate output
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.max_colwidth", None)

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
IP Address Whitelisting
"""


class IPConfig(BaseModel):
    whitelist: list[str] = ["localhost", "127.0.0.1"]
    public_ips: list[str] = []  # TODO: add whitelisted public IPs here


ip_config = IPConfig()


def is_ip_allowed(request: Request):
    client_host = request.client.host
    return client_host in ip_config.whitelist or client_host in ip_config.public_ips


"""
FastAPI app
"""

# Create the app with minimal initial setup
app = FastAPI(title="meetup_bot API",
              openapi_url="/meetup_bot.json"
)

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
    hashed_password = Required(str)
    email = Optional(str)


# Move database initialization to lifespan context
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB connection
    db.bind(provider='postgres',
            user=DB_USER,
            password=DB_PASS.strip('"'),
            host=DB_HOST,
            database=DB_NAME,
            port=DB_PORT)
    db.generate_mapping(create_tables=True)

    # Create initial user if needed (moved from startup_event)
    with db_session:
        if not UserInfo.exists(username=DB_USER):
            hashed_password = get_password_hash(DB_PASS)
            UserInfo(username=DB_USER, hashed_password=hashed_password)

    print("Application startup complete")

    yield  # Application runs here

    # Cleanup
    print("Application shutdown")
    db.disconnect()

app = FastAPI(
    title="meetup_bot API",
    openapi_url="/meetup_bot.json",
    lifespan=lifespan
)


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


async def ip_whitelist_or_auth(request: Request, current_user: User = Depends(get_current_active_user)):
    if is_ip_allowed(request):
        return {"bypass_auth": True}

    return current_user


def check_auth(auth: dict | User) -> None:
    """
    Shared function to check authentication result.
    Raises an HTTPException if authentication fails.
    """
    if isinstance(auth, dict) and auth.get("bypass_auth"):
        print("Authentication bypassed due to whitelisted IP")
    elif not isinstance(auth, User):
        raise HTTPException(status_code=401, detail="Unauthorized")


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


@app.get("/healthz", status_code=200)
def health_check():
    """Smoke test to check if the app is running"""
    return {"status": "ok"}


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
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
    except KeyError as e:
        print(f"{Fore.RED}{ERROR:<10}{Fore.RESET}KeyError: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return access_token, refresh_token


@api_router.get("/events")
def get_events(auth: dict = Depends(ip_whitelist_or_auth),
               location: str = "Oklahoma City",
               exclusions: str = "Tulsa",
               current_user: User = Depends(get_current_active_user)
    ):
    """
    Query upcoming Meetup events

    Args:
        location (str): location to search for events
        exclusions (str): location to exclude from search
    """

    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # default exclusions
    exclusion_list = ["36\u00b0N", "Nerdy Girls"]

    # if exclusions, add to list of exclusions
    if exclusions is not None:
        exclusions = exclusions.split(",")
        exclusion_list = exclusion_list + exclusions

    # Get all events with the specified exclusions
    events = get_all_events(exclusion_list)

    return events


@api_router.get("/check-schedule")
def should_post_to_slack(auth: dict = Depends(ip_whitelist_or_auth), request: Request = None):
    """
    Check if it's time to post to Slack based on the schedule
    """

    with db_session:
        check_and_revert_snooze()  # Check and revert any expired snoozes
        schedule = get_schedule(current_day)

        if schedule and schedule.enabled:
            utc_time, local_time = get_current_schedule_time(schedule)

            # Parse the schedule time
            schedule_time_local = (
                arrow.get(schedule.schedule_time, "HH:mm")
                .replace(year=current_time_local.year, month=current_time_local.month, day=current_time_local.day, tzinfo="UTC")
                .to(tz)
            )

            # Calculate time difference in minutes and round up
            time_diff = abs((schedule_time_local - current_time_local).total_seconds() / 60)
            time_diff_rounded = ceil(time_diff)

            # TODO: walk back to 5-10 minutes vs. 90 minutes
            # Check if current time is within n minutes of scheduled time
            should_post = time_diff_rounded <= 90

            # TODO: verify if it's actually CST or CDT
            return {
                "should_post": should_post,
                "current_time": current_time_local.format("dddd HH:mm ZZZ"),
                "schedule_time": schedule_time_local.format("dddd HH:mm ZZZ"),
                "time_diff_minutes": time_diff_rounded,
            }

        # If no schedule found or not enabled
        elif not schedule or not schedule.enabled:
            return {
                "should_post": False,
            }


@api_router.post("/slack")
def post_slack(
    auth: dict = Depends(ip_whitelist_or_auth),
    location: str = "Oklahoma City",
    exclusions: str = "Tulsa",
    channel_name: str = None,
    current_user: User = Depends(get_current_active_user),
    override: bool = bypass_schedule,
):
    """
    Post to slack

    Calls main function to post formatted message to predefined channel
    """

    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Get events and check for errors
    events = get_all_events([exclusions] if exclusions else None)
    if not events:
        return {"message": "No upcoming events found", "status": "info"}

    # Format messages directly from events data
    try:
        # Format each event into a Slack message
        messages = []
        for event in events:
            message = f'• {event["date"]} *{event["name"]}* <{event["eventUrl"]}|{event["title"]}> '
            messages.append(message)

        if not messages:
            return {"message": "No upcoming events to post", "status": "info"}

        # if channel_name is not None, post to channel as one concatenated string
        if channel_name is not None:
            # get channel id from chan_dict
            channel_id = chan_dict[channel_name]
            # post to single channel
            response = send_message("\n".join(messages), channel_id)
            if not response:
                return {"message": "Failed to send message to Slack", "status": "error"}
        else:
            # post to all channels
            channels = load_channels()
            for name, id in channels.items():
                response = send_message("\n".join(messages), id)
                if not response:
                    return {"message": f"Failed to send message to channel {name}", "status": "error"}

        return {"message": messages, "status": "success"}
    except Exception as e:
        return {"message": f"Error posting to Slack: {str(e)}", "status": "error"}


@api_router.post("/snooze")
def snooze_slack_post(
    duration: str,
    auth: dict = Depends(ip_whitelist_or_auth),
    ):
    """
    Snooze the Slack post for the specified duration

    Args:
        duration (str): Duration to snooze the post. Valid options are:
                        "5_minutes", "next_scheduled", "rest_of_week"
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        snooze_schedule(duration)
        return {"message": f"Slack post snoozed for {duration}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# TODO: test IP whitelisting
@api_router.get("/schedule")
def get_current_schedule(auth: dict | User = Depends(ip_whitelist_or_auth)):
    """
    Get the current schedule including any active snoozes
    """
    check_auth(auth)

    with db_session:
        check_and_revert_snooze()  # Check and revert any expired snoozes
        schedules = []
        for day in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]:
            schedule = get_schedule(day)
            if schedule:
                schedules.append(
                    {
                        "day": schedule.day,
                        "schedule_time": schedule.schedule_time,
                        "enabled": schedule.enabled,
                        "snooze_until": schedule.snooze_until,
                        "original_schedule_time": schedule.original_schedule_time,
                    }
                )

    return {"schedules": schedules}


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

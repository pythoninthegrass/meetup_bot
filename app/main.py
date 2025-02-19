#!/usr/bin/env python3

import arrow
import asyncio
import json
import pandas as pd
import sys
import time
from app.core.meetup_query import get_all_events
from app.core.sign_jwt import main as gen_token
from app.core.slackbot import *
from app.utils.schedule import (
    TZ,
    get_schedule,
    snooze_schedule,
)
from colorama import Fore
from config import *
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta, timezone
from decouple import config
from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.models import SecuritySchemeType
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from fastapi.security.base import SecurityBase
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.templating import Jinja2Templates
from icecream import ic
from jose import JWTError, jwt
from math import ceil
from passlib.context import CryptContext
from pathlib import Path
from pony.orm import Database, Optional, PrimaryKey, Required, Set, db_session
from pydantic import BaseModel
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
COOKIE_NAME = "session_token"  # Name of the cookie that will store the session token
IS_DEV = HOST in ["localhost", "127.0.0.1", "0.0.0.0"] or PORT == 3000  # Development mode check
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
app = FastAPI(
    title="meetup_bot API",
    openapi_url="/meetup_bot.json",
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


# Initialize database connection
db.bind(provider='postgres',
        user=DB_USER,
        password=DB_PASS.strip('"'),
        host=DB_HOST,
        database=DB_NAME,
        port=DB_PORT)
db.generate_mapping(create_tables=True)

# Create initial user if needed
with db_session:
    if not UserInfo.exists(username=DB_USER):
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash(DB_PASS)
        UserInfo(username=DB_USER, hashed_password=hashed_password)


"""
Authentication
"""

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
    expire = datetime.now(UTC) + expires_delta if expires_delta else datetime.now(UTC) + timedelta(minutes=TOKEN_EXPIRE)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


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


# Authentication schemes
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    auto_error=False
)

class CookieOrHeaderToken(SecurityBase):
    def __init__(
        self,
        *,
        cookie_name: str = COOKIE_NAME,
        scheme_name: str | None = None,
        description: str | None = None,
        auto_error: bool = True,
    ):
        self.cookie_name = cookie_name
        self.scheme_name = scheme_name or self.__class__.__name__
        self.description = description
        self.auto_error = auto_error
        self.model = {
            "type": SecuritySchemeType.http,
            "scheme": "bearer",
        }

    async def __call__(self, request: Request) -> str | None:
        # First try cookie
        cookie_token = request.cookies.get(self.cookie_name)
        if cookie_token:
            return cookie_token

        # Then try Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None

        scheme, token = get_authorization_scheme_param(authorization)
        if scheme.lower() != "bearer":
            return None

        return token

# Security schemes
security = CookieOrHeaderToken(auto_error=False)  # Don't auto-error so we can try form auth
oauth_form_dependency = Depends(OAuth2PasswordRequestForm)

# Update app to include both security schemes
app.swagger_ui_init_oauth = {
    "usePkceWithAuthorizationCodeGrant": True,
    "clientId": "meetup_bot",
}

async def get_current_user(
    request: Request,
    token: str | None = Depends(security),
    form_token: str | None = Depends(oauth2_scheme),
):
    """Get current user from session cookie, bearer token, or form authentication"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try cookie/header token first, then form token
    token_to_verify = token or form_token
    if not token_to_verify:
        raise credentials_exception

    try:
        payload = jwt.decode(token_to_verify, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as err:
        raise credentials_exception from err

    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


current_user_dependency = Depends(get_current_user)

async def get_current_active_user(current_user: User = current_user_dependency):
    """Get current active user"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")

    return current_user

current_active_user_dependency = Depends(get_current_active_user)

async def ip_whitelist_or_auth(request: Request, current_user: User = current_active_user_dependency):
    if is_ip_allowed(request):
        return {"bypass_auth": True}

    return current_user

ip_whitelist_auth_dependency = Depends(ip_whitelist_or_auth)


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
async def login_for_oauth_token(response: Response, form_data: OAuth2PasswordRequestForm = oauth_form_dependency):
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

    # Set the session cookie
    response.set_cookie(
        key=COOKIE_NAME,
        value=oauth_token,
        httponly=True,              # Prevents JavaScript access
        secure=not IS_DEV,          # Only require HTTPS in production
        samesite="lax",             # Protects against CSRF
        max_age=TOKEN_EXPIRE * 60,  # Convert minutes to seconds
        expires=datetime.now(UTC) + oauth_token_expires
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
        response = RedirectResponse(url="/docs", status_code=303)

        # Create and set session cookie
        oauth_token_expires = timedelta(minutes=TOKEN_EXPIRE)
        oauth_token = create_access_token(
            data={"sub": username}, expires_delta=oauth_token_expires
        )

        response.set_cookie(
            key=COOKIE_NAME,
            value=oauth_token,
            httponly=True,
            secure=not IS_DEV,  # Only require HTTPS in production
            samesite="lax",
            max_age=TOKEN_EXPIRE * 60,
            expires=datetime.now(UTC) + oauth_token_expires
        )


        return response

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password"
    )


# TODO: use refresh token to get new access token
@api_router.get("/token")
def generate_token(current_user: User = current_active_user_dependency):
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
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

    return access_token, refresh_token


@api_router.get("/events")
def get_events(auth: dict = ip_whitelist_auth_dependency,
               location: str = "Oklahoma City",
               exclusions: str = "Tulsa",
               current_user: User = current_active_user_dependency
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
def should_post_to_slack(auth: dict = ip_whitelist_auth_dependency, request: Request = None):
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
    auth: dict = ip_whitelist_auth_dependency,
    location: str = "Oklahoma City",
    exclusions: str = "Tulsa",
    channel_name: str = None,
    current_user: User = current_active_user_dependency,
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
    auth: dict = ip_whitelist_auth_dependency,
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
        current_time = arrow.now(tz)
        current_day = current_time.format("dddd")
        schedule = get_schedule(current_day)

        if not schedule:
            raise HTTPException(status_code=404, detail=f"No schedule found for {current_day}")

        snooze_schedule(schedule, duration)
        return {"message": f"Slack post snoozed for {duration}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# TODO: test IP whitelisting
@api_router.get("/schedule")
def get_current_schedule(auth: dict | User = ip_whitelist_auth_dependency):
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

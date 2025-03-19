#!/usr/bin/env python3

import arrow
import asyncio
import json
import pandas as pd
import sys
import time
from app.core.auth import (
    OAuth2PasswordRequestForm,
    Token,
    TokenData,
    User,
    check_auth,
    current_active_user_dependency,
    current_user_dependency,
    ip_whitelist_auth_dependency,
    oauth_form_dependency,
)
from app.core.db import (
    authenticate_user,
    create_access_token,
    db,
    db_session,
    get_user,
    init_db,
    load_user,
    verify_password,
)
from app.core.meetup_query import get_all_events
from app.core.sign_jwt import main as gen_token
from app.core.slackbot import *
from app.utils.schedule import (
    TZ,
    check_and_revert_snooze,
    get_current_schedule_time,
    get_current_schedules,
    get_schedule,
    should_post_to_slack,
    snooze_schedule,
)
from colorama import Fore
from config import *
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta, timezone
from decouple import config
from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from icecream import ic
from math import ceil
from pathlib import Path
from pydantic import BaseModel

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

# Create the app with minimal initial setup
app = FastAPI(
    title="meetup_bot API",
    openapi_url="/meetup_bot.json",
)

# add `/api` route in front of all other endpoints
api_router = APIRouter(prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Update app to include both security schemes
app.swagger_ui_init_oauth = {
    "usePkceWithAuthorizationCodeGrant": True,
    "clientId": "meetup_bot",
}


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
def should_post_to_slack_endpoint(auth: dict = ip_whitelist_auth_dependency, request: Request = None):
    """
    Check if it's time to post to Slack based on the schedule
    """
    # Use the centralized function from schedule.py
    return should_post_to_slack()


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

    # Check schedule first if not overridden
    if not override:
        schedule_check = should_post_to_slack(override)
        if not schedule_check["should_post"]:
            reason = schedule_check.get("reason", "Not scheduled for posting at this time")
            return {"message": f"Skipping Slack post: {reason}", "status": "info"}

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
    current_user: User = current_active_user_dependency,
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


@api_router.get("/schedule")
def get_current_schedule(auth: dict | User = ip_whitelist_auth_dependency):
    """
    Get the current schedule including any active snoozes
    """
    check_auth(auth)

    # Use the centralized function from schedule.py
    schedules = get_current_schedules()

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

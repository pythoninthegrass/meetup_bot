#!/usr/bin/env python3

import arrow
import os
import pandas as pd
import sys
import time
import uvicorn
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
from pony.orm import *
from pydantic import BaseModel
from sign_jwt import main as gen_token
from slackbot import *

# verbose icecream
ic.configureOutput(includeContext=True)

# logging prefixes
info = "INFO:"
error = "ERROR:"
warning = "WARNING:"

# logs
# pony.options.CUT_TRACEBACK = False
# logging.basicConfig(level=logging.DEBUG)

# cache
# requests_cache.install_cache("api_cache", expire_after=3600)

# env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()
csv_fn = Path('raw/output.csv')
json_fn = Path('raw/output.json')
TZ = config('TZ', default='America/Chicago')
loc_time = arrow.now().to(TZ)
time.tzset()

# pandas don't truncate output
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

# index
templates = Jinja2Templates(directory=Path("resources/templates"))

# creds
if env.exists():
    TTL = config('TTL', default=3600, cast=int)
    HOST = config('HOST')
    PORT = config('PORT', default=3000, cast=int)
    SECRET_KEY = config('SECRET_KEY')
    ALGORITHM = config('ALGORITHM', default='HS256')
    TOKEN_EXPIRE = config('TOKEN_EXPIRE', default=30, cast=int)
    DB_NAME = config('DB_NAME')
    DB_USER = config('DB_USER')
    DB_PASS = config('DB_PASS')
    DB_PORT = config('DB_PORT', default=5432, cast=int)

else:
    TTL = int(os.getenv('TTL', default=3600))
    HOST = os.getenv('HOST')
    PORT = int(os.getenv('PORT', default=3000))
    SECRET_KEY = os.getenv('SECRET_KEY')
    ALGORITHM = os.getenv('ALGORITHM', default='HS256')
    TOKEN_EXPIRE = int(os.getenv('TOKEN_EXPIRE', default=30))
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASS = os.getenv('DB_PASS')
    DB_PORT = int(os.getenv('DB_PORT', default=5432))


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
Scheduler
"""

# TODO: rocketry or wakaq


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
# db.bind(provider='sqlite', filename=DB_NAME, create_db=True)              # local db
db.bind(provider='sqlite', filename=':memory:')                             # in-memory db

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
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login for access token"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=TOKEN_EXPIRE)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


# @app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Read users me"""
    return current_user


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

@app.on_event('startup')
def startup_event():
    """
    Run startup event
    """

    # TODO: background tasks: generate access and refresh tokens every 55 minutes(fastapi/rocketry); post to slack every 24 hours

    # create user
    with db_session:
        if not UserInfo.exists(username=DB_USER):
            hashed_password = get_password_hash(DB_PASS)
            UserInfo(username=DB_USER, hashed_password=hashed_password)

    # generate access and refresh tokens
    tokens = gen_token()

    global access_token
    access_token = tokens['access_token']

    global refresh_token
    refresh_token = tokens['refresh_token']

    return access_token, refresh_token


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    with open(Path("resources/templates/login.html")) as f:
        return HTMLResponse(content=f.read(), status_code=200)


@app.post("/auth/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Redirect to "/docs" from index page if user successfully logs in with HTML form"""
    if load_user(username) and verify_password(password, load_user(username).hashed_password):
        return RedirectResponse(url="/docs", status_code=303)


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

    # generate access and refresh tokens
    tokens = gen_token()
    access_token = tokens['access_token']
    refresh_token = tokens['refresh_token']

    return access_token, refresh_token


# TODO: decouple export from formatted response
@api_router.get("/events")
def get_events(location: str = "Oklahoma City", exclusions: str = "Tulsa", current_user: User = Depends(get_current_active_user)):
    """
    Query upcoming Meetup events
    """

    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # if exclusions, add to list of exclusions
    if exclusions:
        exclusions = exclusions.split(",")
    else:
        exclusions = []

    response = send_request(access_token, query, vars)

    export_to_file(response, format, exclusions=exclusions)                  # csv/json

    # TODO: log decorator
    # third-party query
    output = []
    for url in url_vars:
        response = send_request(access_token, url_query, f'{{"urlname": "{url}"}}')
        # append to output dict if the response is not empty
        if len(format_response(response, exclusions=exclusions)) > 0:
            output.append(response)
        else:
            print(f"{Fore.GREEN}{info:<10}{Fore.RESET}No upcoming events for {url} found")
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
def post_slack(location: str = "Oklahoma City", exclusions: str = "Tulsa", current_user: User = Depends(get_current_active_user)):
    """
    Post to slack

    Calls main function to post formatted message to predefined channel
    """

    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    get_events(location, exclusions)
    msg = fmt_json(json_fn)
    send_message('\n'.join(msg))

    return ic(msg)


# routes
app.include_router(api_router)


def main():
    """
    Run app
    """

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

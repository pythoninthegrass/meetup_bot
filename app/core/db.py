from datetime import UTC, datetime, timedelta
from decouple import config
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pony.orm import Database, Optional, PrimaryKey, Required, Set, db_session
from pydantic import BaseModel

# Database configuration
DB_NAME = config("DB_NAME")
DB_USER = config("DB_USER")
DB_PASS = config("DB_PASS")
DB_HOST = config("DB_HOST")
DB_PORT = config("DB_PORT", default=5432, cast=int)

# JWT configuration
SECRET_KEY = config("SECRET_KEY")
ALGORITHM = config("ALGORITHM", default="HS256")
TOKEN_EXPIRE = config("TOKEN_EXPIRE", default=30, cast=int)

# Initialize database
db = Database()


# User model
class UserInfo(db.Entity):
    username = Required(str, unique=True)
    hashed_password = Required(str)
    email = Optional(str)


# Initialize database connection
def init_db():
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


# Authentication models
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


# Password handling
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    """Validate plaintext password against hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Return hashed password"""
    return pwd_context.hash(password)


# User management
def get_user(username: str):
    """Get user from database"""
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


def load_user(username: str):
    """Load user from database"""
    with db_session:
        user = UserInfo.get(username=username)
        if user:
            return user
        else:
            raise HTTPException(status_code=404, detail="User not found")


# Token management
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create access token"""
    to_encode = data.copy()
    expire = datetime.now(UTC) + expires_delta if expires_delta else datetime.now(UTC) + timedelta(minutes=TOKEN_EXPIRE)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

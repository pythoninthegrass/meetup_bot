#!/usr/bin/env python3

import jwt
import requests
import time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from decouple import config
from icecream import ic
from pathlib import Path
from urllib.parse import urlencode

# env
env = Path('.env')
priv_key = Path('jwt_priv.pem')
pub_key = Path('jwt_pub.key')

CLIENT_ID = config('CLIENT_ID')
CLIENT_SECRET = config('CLIENT_SECRET')
SIGNING_KEY_ID = config('SIGNING_KEY_ID')
SIGNING_SECRET = config('SIGNING_SECRET')
TOKEN_URL = config('TOKEN_URL')
REDIRECT_URI = config('REDIRECT_URI')
JWT_LIFE_SPAN = config('JWT_LIFE_SPAN', default=120, cast=int)


with open(priv_key, 'rb') as file:
    private_key = serialization.load_pem_private_key(
        file.read(),
        password=None,
        backend=default_backend()
    )

with open(pub_key, 'rb') as file:
    public_key = serialization.load_pem_public_key(
        file.read(),
        backend=default_backend()
    )

headers = {
    "alg": 'RS256',
    "typ": 'JWT',
    "Accept": 'application/json',
    "Content-Type": 'application/x-www-form-urlencoded'
}

payload_data = {
    "audience": 'api.meetup.com',
    "kid": SIGNING_KEY_ID,
    "sub": CLIENT_ID,
    "iss": CLIENT_SECRET,
    "exp": time.time() + JWT_LIFE_SPAN
}


def sign_token():
    """Generate signed JWT"""

    payload = jwt.encode(
        headers=headers,
        payload=payload_data,
        key=private_key,
        algorithm='RS256'
    )

    return payload


def verify_token(token):
    """Verify signed JWT against public key"""

    try:
        decoded_token = jwt.decode(
            jwt=token,
            key=public_key,
            issuer=CLIENT_SECRET,
            verify=True,
            algorithms=['RS256']
        )
        print(f"[decoded_token]: {decoded_token}")

        return True
    except (
        jwt.exceptions.InvalidTokenError,
        jwt.exceptions.InvalidSignatureError,
        jwt.exceptions.InvalidIssuerError,
        jwt.exceptions.ExpiredSignatureError
        ) as e:
        print(f"[error]: {e}")

        return False


def get_access_token(token):
    """Post token to auth server to get access token"""

    payload = {
        "grant_type": 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        "assertion": token,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "audience": 'api.meetup.com',
        "exp": time.time() + JWT_LIFE_SPAN
    }
    payload = urlencode(payload)

    return requests.request("POST", TOKEN_URL, headers=headers, data=payload)


# TODO: empty 200 response
if __name__ == "__main__":
    token = sign_token()
    verify_token(token)
    access_token = get_access_token(token)
    ic(access_token.json())

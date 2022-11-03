#!/usr/bin/env python3

import base64
import jwt
import os
import pathlib
import requests
import sys
import time
from colorama import Fore
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from decouple import config
from icecream import ic
from pathlib import Path
from urllib.parse import urlencode

# verbose icecream
# ic.configureOutput(includeContext=True)

# logging prefixes
info = "INFO:"
error = "ERROR:"
warning = "WARNING:"

# creds
priv_key = Path('jwt_priv.pem')
pub_key = Path('jwt_pub.key')
SELF_ID = config('SELF_ID')
CLIENT_ID = config('CLIENT_ID')
CLIENT_SECRET = config('CLIENT_SECRET')
SIGNING_KEY_ID = config('SIGNING_KEY_ID')
SIGNING_SECRET = config('SIGNING_SECRET')
TOKEN_URL = config('TOKEN_URL')
REDIRECT_URI = config('REDIRECT_URI')
JWT_LIFE_SPAN = config('JWT_LIFE_SPAN', default=120, cast=int)

# load private key
if isinstance(priv_key, pathlib.PosixPath) and priv_key.exists():
    with open(priv_key, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            data=f.read(),
            password=None,
            backend=default_backend()
        )
else:
    # decode base64
    private_key = base64.b64decode(priv_key)
    # load private key from env
    private_key = serialization.load_pem_private_key(
        data=private_key,
        password=None,
        backend=default_backend()
    )

if isinstance(pub_key, pathlib.PosixPath) and pub_key.exists():
    with open(pub_key, 'rb') as f:
        public_key = serialization.load_pem_public_key(
            data=f.read(),
            backend=default_backend()
        )
else:
    # decode base64
    public_key = base64.b64decode(pub_key)
    # load public key
    public_key = serialization.load_pem_public_key(
        data=public_key,
        backend=default_backend()
    )

headers = {
    "alg": 'RS256',
    "typ": 'JWT',
    "Accept": 'application/json',
    "Content-Type": 'application/x-www-form-urlencoded'
}


# TODO: Fix `Signature has expired\n[ERROR] Exception in ASGI application`; scheduler.sh only works for ~7 tries / 1 hour
def gen_payload_data():
    """
    Generate payload data for JWT

    Avoids `invalid_grant` by getting a new `exp` value during signing
    """

    payload_data = {
        "audience": 'api.meetup.com',
        "kid": SIGNING_KEY_ID,
        "sub": SELF_ID,
        "iss": CLIENT_SECRET,
        "exp": time.time() + int(JWT_LIFE_SPAN)
    }

    return payload_data


def sign_token():
    """Generate signed JWT"""

    payload_data = gen_payload_data()

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
        print(f"{Fore.GREEN}{info:<10}{Fore.RESET}Success! Token verified.")
        return True
    except jwt.exceptions.ExpiredSignatureError as e:
        print(f"{Fore.YELLOW}{warning:<10}{Fore.RESET}Token has expired: {e}")
        return False
    except (
        jwt.exceptions.InvalidTokenError,
        jwt.exceptions.InvalidSignatureError,
        jwt.exceptions.InvalidIssuerError,
        ) as e:
        print(f"{Fore.RED}{error:<10}{Fore.RESET}{e}")
        sys.exit(1)


def get_access_token(token):
    """Post token to auth server to get access token"""

    payload = {
        "grant_type": 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        "assertion": token,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "audience": 'api.meetup.com',
        "exp": time.time() + int(JWT_LIFE_SPAN)
    }
    payload = urlencode(payload)

    return requests.request("POST", TOKEN_URL, headers=headers, data=payload)


def main():
    """Generate signed JWT, verify, and get access token"""

    # sign JWT
    token = sign_token()

    # verify JWT
    verify_token(token)

    # get access and refresh tokens
    res = get_access_token(token)

    return res.json()


if __name__ == "__main__":
    main()

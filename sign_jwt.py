#!/usr/bin/env python3

import jwt
import os
import requests
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

# env
env = Path('.env')
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

if Path(priv_key).exists():
    with open(priv_key, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            data=f.read(),
            password=None,
            backend=default_backend()
        )
else:
    # load private key from env
    private_key = config('PRIVATE_KEY')
    # insert line breaks at \n with os.linesep
    private_key = os.linesep.join(private_key.split('\\n'))
    # convert to bytes
    private_key = private_key.encode('utf-8')
    # load private key
    private_key = serialization.load_pem_private_key(
        data=private_key,
        password=None,
        backend=default_backend()
    )

if Path(pub_key).exists():
    with open(pub_key, 'rb') as f:
        public_key = serialization.load_pem_public_key(
            data=f.read(),
            backend=default_backend()
        )
else:
    # load public key from env
    public_key = config('PUBLIC_KEY')
    # insert line breaks at \n with os.linesep
    public_key = os.linesep.join(public_key.split('\\n'))
    # convert to bytes
    public_key = public_key.encode('utf-8')
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

payload_data = {
    "audience": 'api.meetup.com',
    "kid": SIGNING_KEY_ID,
    "sub": SELF_ID,
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

    # TODO: log decorator
    try:
        decoded_token = jwt.decode(
            jwt=token,
            key=public_key,
            issuer=CLIENT_SECRET,
            verify=True,
            algorithms=['RS256']
        )
        # print(f"[decoded_token]: {decoded_token}")
        print(f"{Fore.GREEN}{info:<10}{Fore.RESET}Success! Token verified.")

        return True
    except (
        jwt.exceptions.InvalidTokenError,
        jwt.exceptions.InvalidSignatureError,
        jwt.exceptions.InvalidIssuerError,
        jwt.exceptions.ExpiredSignatureError
        ) as e:
        print(f"{Fore.RED}{error:<10}{Fore.RESET}{e}")

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


def main():
    """Generate signed JWT, verify, and get access token"""

    token = sign_token()
    verify_token(token)
    access_token = get_access_token(token)

    # TODO: fastapi_login setup for access_token
    # return access_token.json()


if __name__ == "__main__":
    main()

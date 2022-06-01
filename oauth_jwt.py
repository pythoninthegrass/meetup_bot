#!/usr/bin/env python3

import arrow
import logging as log
import requests
from authlib.jose import jwt
from cryptography.hazmat.primitives import serialization
from decouple import config
from icecream import ic
from pathlib import Path

# verbose icecream
ic.configureOutput(includeContext=True)

log.basicConfig(level=log.DEBUG)

# env
home = Path.home()
env = Path('.env')
cwd = Path.cwd()

# creds
if env.exists():
    CLIENT_ID = config('CLIENT_ID')
    CLIENT_SECRET = config('CLIENT_SECRET')
    SIGNING_KEY_ID = config('SIGNING_KEY_ID')
    REDIRECT_URI = config('REDIRECT_URI')
    TOKEN_URL = config('TOKEN_URL')
    AUTH_BASE_URL = config('AUTH_BASE_URL')
    TOKEN_URL = config('TOKEN_URL')

# jwt flow
fn = Path('jwt_priv.pem')
with open(fn, 'rb') as cert:
    key = serialization.load_pem_private_key(
        cert.read(),
        password=None
    )

# print private key
priv_key = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)
# print public key
pub_key = key.public_key()
pub_key = pub_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)

token_endpoint = TOKEN_URL


# https://stackoverflow.com/a/56723016
def gen_access_token(client, grant_type):
    # log.debug('Not used yet in the JWT: %s', client)
    # log.debug('Not used yet in the JWT: %s', grant_type)

    exp = arrow.utcnow().shift(seconds=120).int_timestamp

    # TODO: verify `sub` and `iss` are correct per https://www.meetup.com/api/authentication/#p04-jwt-flow-section
    payload = {
        "sub": CLIENT_ID,           # "{AUTHORIZED_MEMBER_ID}"
        "iss": CLIENT_SECRET,       # "{YOUR_CLIENT_KEY}"
        "aud": "api.meetup.com",
        "exp": exp                  # "{EXPIRATION_TIME_IN_SECONDS}"
    }

    header = {
        'kid': SIGNING_KEY_ID,
        'typ': 'JWT',
        'alg': 'RS256',
    }

    try:
        token = jwt.encode(header, payload, key=priv_key)
        claims = jwt.decode(token, open('jwt_pub.key', 'r').read())
        claims.validate()
    except Exception as e:
        log.debug('JWT exception', e)
        log.debug(
            "jwt encoded:{}\n decoded :{} \n header:{}".format(
                token, claims, claims.header)
            )

    ic(token.decode('UTF-8'), claims)

    return token


# OAUTH2_REFRESH_TOKEN_GENERATOR = True

# use generator function to generate access token
OAUTH2_ACCESS_TOKEN_GENERATOR_ARGS = {
    'client': CLIENT_ID,
    'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
    # 'grant_type': 'authorization_code',
}

gen_access_token(**OAUTH2_ACCESS_TOKEN_GENERATOR_ARGS)

"""
Testing w/httpie (https://github.com/teracyhq/httpie-jwt-auth)

http --auth-type=jwt --auth=${token} https://secure.meetup.com/oauth2/access -h

# TODO: currently getting 'HTTP/1.1 400 Bad Request'
"""

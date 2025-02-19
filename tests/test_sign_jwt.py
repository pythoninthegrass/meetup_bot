import jwt
import pytest
import requests
import time
from app.core.sign_jwt import gen_payload_data, get_access_token, main, sign_token, verify_token
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_private_key():
    # Generate a test private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    return private_key


@pytest.fixture
def mock_public_key(mock_private_key):
    return mock_private_key.public_key()


def test_gen_payload_data():
    with patch('time.time', return_value=1000000):
        payload = gen_payload_data()
        assert payload['exp'] == 1000000 + 120  # JWT_LIFE_SPAN is 120
        assert 'sub' in payload
        assert 'iss' in payload
        assert 'aud' in payload


def test_sign_token(mock_private_key):
    with patch('app.core.sign_jwt.private_key', mock_private_key), \
         patch('app.core.sign_jwt.SIGNING_KEY_ID', 'test_key_id'), \
         patch('app.core.sign_jwt.CLIENT_ID', 'test_client_id'), \
         patch('app.core.sign_jwt.SELF_ID', 'test_self_id'):
        token = sign_token()
        assert isinstance(token, str)
        # Verify the token structure
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert 'exp' in decoded
        assert decoded['iss'] == 'test_client_id'
        assert decoded['sub'] == 'test_self_id'
        assert decoded['aud'] == 'api.meetup.com'


def test_verify_token_valid(mock_private_key, mock_public_key):
    with patch('app.core.sign_jwt.private_key', mock_private_key), \
         patch('app.core.sign_jwt.public_key', mock_public_key), \
         patch('app.core.sign_jwt.CLIENT_ID', 'test_client_id'), \
         patch('app.core.sign_jwt.SELF_ID', 'test_self_id'), \
         patch('time.time', return_value=1000000):
        # Create a token that won't expire immediately
        token = jwt.encode(
            {
                'exp': time.time() + 300,  # 5 minutes in the future
                'iss': 'test_client_id',
                'sub': 'test_self_id',
                'aud': 'api.meetup.com'
            },
            mock_private_key,
            algorithm='RS256'
        )

        # Mock jwt.decode to return a valid result
        with patch('jwt.decode', return_value={'exp': time.time() + 300}):
            assert verify_token(token) is True


def test_verify_token_expired(mock_private_key, mock_public_key):
    with patch('app.core.sign_jwt.private_key', mock_private_key), \
         patch('app.core.sign_jwt.public_key', mock_public_key), \
         patch('app.core.sign_jwt.CLIENT_ID', 'test_client_id'), \
         patch('time.time', return_value=1000000):
        token = sign_token()
        # Move time forward past expiration
        with patch('time.time', return_value=1000000 + 200):
            assert verify_token(token) is False


def test_get_access_token_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token"
    }
    mock_response.raise_for_status.return_value = None

    with patch('requests.request', return_value=mock_response):
        result = get_access_token("test_token")
        assert result["access_token"] == "test_access_token"
        assert result["refresh_token"] == "test_refresh_token"


def test_get_access_token_failure():
    with patch('requests.request') as mock_request:
        mock_request.side_effect = requests.exceptions.RequestException("Test error")
        result = get_access_token("test_token")
        assert result is None
        mock_request.assert_called_once()


def test_main_success(mock_private_key, mock_public_key):
    mock_tokens = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token"
    }

    with patch('app.core.sign_jwt.private_key', mock_private_key), \
         patch('app.core.sign_jwt.public_key', mock_public_key), \
         patch('app.core.sign_jwt.CLIENT_ID', 'test_client_id'), \
         patch('app.core.sign_jwt.get_access_token', return_value=mock_tokens), \
         patch('jwt.decode', return_value={'exp': time.time() + 300}):
        result = main()
        assert result == mock_tokens


def test_main_failure(mock_private_key, mock_public_key):
    with patch('app.core.sign_jwt.private_key', mock_private_key), \
         patch('app.core.sign_jwt.public_key', mock_public_key), \
         patch('app.core.sign_jwt.CLIENT_ID', 'test_client_id'), \
         patch('app.core.sign_jwt.get_access_token', return_value=None), \
         patch('jwt.decode', return_value={'exp': time.time() + 300}):
        result = main()
        assert result is None

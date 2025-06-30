import requests
from decouple import config

base_url = config('URL', default='http://localhost')
if base_url == 'http://localhost':
    port = config('PORT', default='3000')
    url = f"{base_url}:{port}"
else:
    url = base_url

response = requests.get(f"{url}/healthz")


def test_healthz_endpoint():
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    assert response.text == '{"status":"ok"}', f"Unexpected response content: {response.text}"

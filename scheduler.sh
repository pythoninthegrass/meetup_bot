#!/usr/bin/env sh

# TODO: generate access and refresh tokens every 55 minutes

# shellcheck disable=SC1091,SC3037,SC3045,SC2046

# env
if test -f ".env"; then
	set -a; . .env >/dev/null 2>&1; set +a
fi
test -n "${DB_USER}" || read -p "DB_USER: " DB_USER
test -n "${DB_PASS}" || read -sp "DB_PASS: " DB_PASS

# strip double quotes from env vars if they exist
DB_USER=$(echo "$DB_USER" | sed -e 's/^"//' -e 's/"$//')
DB_PASS=$(echo "$DB_PASS" | sed -e 's/^"//' -e 's/"$//')

# rewrite dev url
if [ $(uname) = "Darwin" ]; then
  URL="${HOST}:${PORT:-3000}"
fi

# smoke test (i.e., index)
# curl -X 'GET' \
#   "${URL}/" \
#   -H 'accept: text/html'

# generate_token
raw=$(curl --no-progress-meter --location --request POST "${URL}/token" \
	--header 'Content-Type: application/x-www-form-urlencoded' \
	--data-urlencode "username=${DB_USER}" \
	--data-urlencode "password=${DB_PASS}")

# split access_token from {"access_token":"TOKEN","token_type":"bearer"}
access_token=$(echo "${raw}" | cut -d '"' -f 4)

# post_slack
send_request() {
	curl --no-progress-meter --location --request POST \
		"${URL}/api/slack" \
		--header "accept: application/json" \
		--header "Authorization: Bearer ${access_token}" \
		--data-urlencode "location=Oklahoma City" \
		--data-urlencode "exclusions=36\u00b0N,Tulsa,Nerdy Girls"
}

# healthchecks ID: 1400  UTC
if [ $(date -u +%H%M) -eq "1400" ]; then
  HEALTHCHECKS_ID="02695fa4-3775-4a52-bd05-1db9883b079f"
  send_request
else
  echo -e "\nTime is $(date -u +%H%M). Not time to run."
  exit 0
fi

# ping healthchecks
curl --no-progress-meter --location --request GET "https://hc-ping.com/${HEALTHCHECKS_ID}"

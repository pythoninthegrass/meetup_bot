#!/usr/bin/env bash

# TODO: generate access and refresh tokens every 55 minutes

# env
[[ -f ".env" ]] && set -a; source .env >/dev/null 2>&1; set +a
[[ -n "${DB_USER}" ]] || read -p "DB_USER: " DB_USER
[[ -n "${DB_PASS}" ]] || read -sp "DB_PASS: " DB_PASS

# strip double quotes from env vars if they exist
DB_USER=$(sed -e 's/^"//' -e 's/"$//' <<<"$DB_USER")
DB_PASS=$(sed -e 's/^"//' -e 's/"$//' <<<"$DB_PASS")

# rewrite dev url
if [[ $(uname) == "Darwin" ]]; then
  URL="${HOST}:${PORT:-3000}"
fi

# index
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
curl --no-progress-meter --location --request POST \
	"${URL}/api/slack" \
	--header "accept: application/json" \
	--header "Authorization: Bearer ${access_token}" \
	--data-urlencode "location=Oklahoma City" \
	--data-urlencode "exclusions=Tulsa"

# healthchecks ID: 1500 and 2300 UTC
if [[ $(date -u +%H%M) -eq "1500" ]]; then
  HEALTHCHECKS_ID="02695fa4-3775-4a52-bd05-1db9883b079f"
elif [[ $(date -u +%H%M) -eq "2300" ]]; then
  HEALTHCHECKS_ID="9f0093c0-6519-4989-b7e8-a12b250c58dd"
else
  echo -e "\nTime is $(date -u +%H%M). Not running healthchecks.io ping"
  exit 0
fi

# ping healthchecks
curl --no-progress-meter --location --request GET "https://hc-ping.com/${HEALTHCHECKS_ID}"

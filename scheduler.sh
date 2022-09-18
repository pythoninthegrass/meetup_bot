#!/usr/bin/env bash

# ENV
# URL="localhost:3000"
[[ -n "${URL}" ]] || URL="https://meetup-bot-bot.herokuapp.com"
[[ -n "${DB_USER}" ]] || read -p "DB_USER: " DB_USER
[[ -n "${DB_PASS}" ]] || read -sp "DB_PASS: " DB_PASS

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

#!/usr/bin/env bash

# index
# curl -X 'GET' \
#   'https://meetup-bot-bot.herokuapp.com/' \
#   -H 'accept: text/html'

# get_token
raw=$(curl --location --request POST 'https://meetup-bot-bot.herokuapp.com/token' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--data-urlencode "username=${DB_USER}" \
--data-urlencode "password=${DB_PASS}")

# split access_token from {"access_token":"TOKEN","token_type":"bearer"}
access_token=$(echo $token | cut -d '"' -f 4)

# post_slack
curl -X 'POST' \
  'https://meetup-bot-bot.herokuapp.com/api/slack?location=Oklahoma%20City&exclusions=Tulsa' \
  -H "accept: application/json" \
  -H "Authorization: Bearer ${access_token}"'

#!/usr/bin/env sh

# shellcheck disable=SC1090,SC1091,SC2034,SC2153,SC3028,SC3037,SC3045,SC2046,SC3001

# source .env
if [ $(uname) = "Darwin" ]; then
	export $(grep -v '^#' .env | xargs)
	MIN=${MIN:-30}
	URL="localhost:${PORT:-3000}"
fi

# get current day of week
day=$(date '+%a')

# strip double quotes from env vars if they exist
DB_USER=$(echo "$DB_USER" | sed -e 's/^"//' -e 's/"$//')
DB_PASS=$(echo "$DB_PASS" | sed -e 's/^"//' -e 's/"$//')

# smoke test (i.e., index)
smoke_test() {
	curl -X 'GET' \
		"${URL}/" \
		-H 'accept: text/html'
}

# generate_token sh equivalent
gen_token() {
	raw=$(curl --no-progress-meter --location --request POST "${URL}/token" \
		--header 'Content-Type: application/x-www-form-urlencoded' \
		--data-urlencode "username=${DB_USER}" \
		--data-urlencode "password=${DB_PASS}")

	# split access_token from {"access_token":"TOKEN","token_type":"bearer"}
	access_token=$(echo "${raw}" | cut -d '"' -f 4)
}

# post_slack sh equivalent
send_request() {
	curl --no-progress-meter --location --request POST \
		"${URL}/api/slack" \
		--header "accept: application/json" \
		--header "Authorization: Bearer ${access_token}" \
		--data-urlencode "location=Oklahoma City" \
		--data-urlencode "exclusions=36\u00b0N,Tulsa,Nerdy Girls"
}

# ping healthchecks
ping_healthchecks() {
	HEALTHCHECKS_ID="02695fa4-3775-4a52-bd05-1db9883b079f"
	curl --no-progress-meter --location --request GET "https://hc-ping.com/${HEALTHCHECKS_ID}"
}

# if current time is within n minutes of scheduled time, then post to slack
date_time() {
	# human readable time
	HMN_TIME=$(date '+%a %b %d %H:%M:%S %Z')
	# convert scheduled run time to seconds
	RUN_TIME=$(date -d "${RUN_TIME}" '+%s')
	# current time in seconds
	CUR_TIME=$(date '+%s')
	# time difference in seconds
	TIME_DIFF=$((CUR_TIME-RUN_TIME))
	# convert minutes to seconds
	MIN=$((MIN*60))
	# * RUN_TIME: 1400 UTC = 0800 CST
	if [ "$TIME_DIFF" -lt "$MIN" ]; then
		printf "%s\n" "Time is ${HMN_TIME}. Posting to $CHANNEL."
		return 0
	else
		printf "%s\n" "Time is ${HMN_TIME}. Not yet time! Exiting..."
		exit 0
	fi
}

# post to slack if it's a weekday
post_slack() {
	case $day in
	Mon|Wed|Fri)
		date_time
		gen_token
		send_request
		ping_healthchecks
		;;
	Tue|Thu)
		# reassign env var to alt channel for tue/thu
		CHANNEL=${CHANNEL2}
		date_time
		gen_token
		send_request
		ping_healthchecks
		;;
	*)
		date_time
		;;
	esac
}

main() {
	# smoke_test
	# gen_token
	# send_request
	# date_time
	post_slack
	# ping_healthchecks
}
main

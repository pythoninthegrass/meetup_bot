#!/usr/bin/env sh

# TODO: generate access and refresh tokens every 55 minutes

# shellcheck disable=SC1091,SC2034,SC2153,SC3037,SC3045,SC2046

test -n "${DB_USER}"
test -n "${DB_PASS}"

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

gen_token() {
	# generate_token
	raw=$(curl --no-progress-meter --location --request POST "${URL}/token" \
		--header 'Content-Type: application/x-www-form-urlencoded' \
		--data-urlencode "username=${DB_USER}" \
		--data-urlencode "password=${DB_PASS}")

	# split access_token from {"access_token":"TOKEN","token_type":"bearer"}
	access_token=$(echo "${raw}" | cut -d '"' -f 4)
}

send_request() {
	# post_slack
	curl --no-progress-meter --location --request POST \
		"${URL}/api/slack" \
		--header "accept: application/json" \
		--header "Authorization: Bearer ${access_token}" \
		--data-urlencode "location=Oklahoma City" \
		--data-urlencode "exclusions=36\u00b0N,Tulsa,Nerdy Girls"
}

post_slack() {
	day=$(date '+%a')
	# TODO: remove Sun && Sat; uncomment if/else blocks; reset time to 1400 UTC
	case $day in
	Sun|Mon|Wed|Fri|Sat)
		# 1400 UTC = 0800 CT
		# if [ $(date -u +%H%M) -eq "1500" ]; then
		# 	printf "%s\n" "Today is $day. Posting to $CHANNEL."
		# 	send_request
		# fi
		printf "%s\n" "Today is $day. Posting to $CHANNEL."
		send_request
		;;
	Tue|Thu)
		# reassign env var to alt channel for Tue/Thur
		CHANNEL=${CHANNEL2}
		# # 1400 UTC = 0800 CT
		# if [ $(date -u +%H%M) -eq "1500" ]; then
		# 	printf "%s\n" "Today is $day. Posting to $CHANNEL."
		# 	send_request
		# fi
		printf "%s\n" "Today is $day. Posting to $CHANNEL."
		send_request
		;;
	*)
		printf "%s\n" "Today is $day. Not time to run."
		exit 0
		;;
	esac
}

ping_healthchecks() {
	# ping healthchecks
	HEALTHCHECKS_ID="02695fa4-3775-4a52-bd05-1db9883b079f"
	curl --no-progress-meter --location --request GET "https://hc-ping.com/${HEALTHCHECKS_ID}"
}

main() {
	gen_token
	post_slack
	ping_healthchecks
}
main

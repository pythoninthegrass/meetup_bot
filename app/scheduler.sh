#!/usr/bin/env sh

# shellcheck disable=SC2046,SC2086,SC2317

# source .env
if [ $(uname) = "Darwin" ]; then
	export $(grep -v '^#' .env | xargs)
	URL="localhost:${PORT:-3000}"
fi

# env vars
# * strip double quotes from env vars if they exist
DB_USER=$(echo "$DB_USER" | sed -e 's/^"//' -e 's/"$//')
DB_PASS=$(echo "$DB_PASS" | sed -e 's/^"//' -e 's/"$//')

# Function to execute curl command
exec_curl() {
	method="$1"
	url="$2"
	shift 2
	curl --no-progress-meter --location \
		--request "$method" \
		"$url" \
		--header 'Content-Type: application/x-www-form-urlencoded' \
		"$@"
}

# smoke test
smoke_test() {
	exec_curl GET "${URL}/healthz" \
		--header "accept: application/json" > /dev/null 2>&1
}

# generate_token sh equivalent
gen_token() {
	raw=$(exec_curl POST "${URL}/token" \
		--data-urlencode "username=${DB_USER}" \
		--data-urlencode "password=${DB_PASS}")

	access_token=$(echo "${raw}" | cut -d '"' -f 4)
}

# send request to specified endpoint
send_request() {
	endpoint="$1"
	data="$2"

	set -e

	case "$endpoint" in
		healthz)
			if smoke_test; then
				echo "Successfully reached ${URL}/healthz"
				exit 0
			else
				echo "Failed to reach ${URL}/healthz"
				exit 1
			fi
			;;
		events)
			gen_token
			exec_curl GET "${URL}/api/events" \
				--header "accept: application/json" \
				--header "Authorization: Bearer ${access_token}"
			;;
		slack)
			gen_token
			exec_curl POST "${URL}/api/slack" \
				--header "accept: application/json" \
				--header "Authorization: Bearer ${access_token}" \
				--data-urlencode "override=${OVERRIDE:-false}" \
				${data:+--data-urlencode "$data"}
			;;
		*)
			echo "Invalid endpoint. Use 'healthz', 'events', or 'slack'."
			exit 1
			;;
	esac

	set +e
}

main() {
	case $# in
		0)
			# default endpoint and data
			endpoint="slack"
			data="override=${OVERRIDE:-false}"
			;;
		2)
			# endpoint and data
			endpoint="$1"
			data="$2"
			;;
		1)
			# endpoint only
			endpoint="$1"
			data=""
			;;
		*)
			echo "Invalid number of arguments."
			echo "Usage: $(basename $0) [endpoint] [data]"
			exit 1
			;;
	esac
	send_request "$endpoint" "$data"
}

main "$@"

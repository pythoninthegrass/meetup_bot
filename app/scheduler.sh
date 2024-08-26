#!/usr/bin/env sh

# shellcheck disable=SC2046

# source .env
if [ $(uname) = "Darwin" ]; then
	export $(grep -v '^#' .env | xargs)
	MIN=${MIN:-30}
	URL="localhost:${PORT:-3000}"
fi

# env vars
# * strip double quotes from env vars if they exist
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
	raw=$(curl --no-progress-meter --location \
		--request POST "${URL}/token" \
		--header 'Content-Type: application/x-www-form-urlencoded' \
		--data-urlencode "username=${DB_USER}" \
		--data-urlencode "password=${DB_PASS}")

	# split access_token from {"access_token":"TOKEN","token_type":"bearer"}
	access_token=$(echo "${raw}" | cut -d '"' -f 4)
}

# post_slack sh equivalent
send_request() {
	curl --no-progress-meter --location \
		--request POST "${URL}/api/slack" \
		--header "accept: application/json" \
		--header "Authorization: Bearer ${access_token}" \
		--data-urlencode "override=${OVERRIDE:-false}"
}

main() {
	# smoke_test
	gen_token
	send_request
}
main

#!/usr/bin/env sh

script_dir=$(cd "$(dirname "$0")" && pwd)
top_dir=$(cd "${script_dir}/.." && pwd)

if [ "$(uname -s)" = "Darwin" ]; then
	export VENV="${top_dir}/.venv"
else
	export VENV="/opt/venv"
fi
export PATH="${VENV}/bin:$HOME/.asdf/bin:$HOME/.asdf/shims:$PATH"

server() {
	gunicorn \
		-w 1 \
		--threads 4 \
		-k uvicorn.workers.UvicornH11Worker main:app \
		--preload \
		-b "0.0.0.0:${PORT:-3000}" \
		--log-file -
}

main() {
	server
}
main "$@"

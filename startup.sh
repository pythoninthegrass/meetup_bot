#!/usr/bin/env bash

export VIRTUAL_ENV="/opt/venv"
export PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
export PATH="${VIRTUAL_ENV}/bin:$HOME/.asdf/bin:$HOME/.asdf/shims:/ms-playwright:$PATH"

# source .venv/bin/activate

gunicorn -w 2 -k uvicorn.workers.UvicornWorker main:app -b 0.0.0.0:${PORT:-3000} --log-file -

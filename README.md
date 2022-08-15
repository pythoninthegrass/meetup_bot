<img alt="gitleaks badge" src="https://img.shields.io/badge/protected%20by-gitleaks-blue">

# meetup_bot

## Summary
Use Meetup Pro API to send Slack messages before events occur.

## Usage
* meetup_bot
  * Dev
    ```bash
    # docker
    docker-compose build --pull --parallel --no-cache
    docker-compose up -d

    # poetry
    poetry install
    poetry run main.py

    # curl/httpie/requests (httpie shown)
    # root
    λ http :3000
    HTTP/1.1 200 OK
    content-length: 25
    content-type: application/json
    date: Thu, 11 Aug 2022 06:22:01 GMT
    server: uvicorn

    {
        "message": "Hello World"
    }

    # get events
    λ http :3000/api/events
    HTTP/1.1 200 OK
    ...

    {
        "city": {
            "3": "Oklahoma City",
            ...
        },
        "date": {
            "3": "2022-08-12T09:30-05:00",
        },
        "description": {
            "3": "If you can't make it to the [UXOK](https://uxok.org/) design conf...",
        },
        "eventUrl": {
            "3": "https://www.meetup.com/okccoffeeandcode/events/287519063",
        },
        "name": {
            "3": "OKC Coffee and Code",
        },
        "title": {
            "3": "UXOK Watch Party",
        }
    }

    # exports to cwd/raw/output.json
    λ http POST :3000/api/export
    HTTP/1.1 200 OK
    ...

    null

    # post formatted query results to slack
    λ http POST :3000/api/slack
    HTTP/1.1 200 OK
    ...

    null
    ```
  * Prod
    * Heroku
      * Setup
        ```bash
        # install
        brew tap heroku/brew && brew install heroku

        # autocomplete + login
        heroku autocomplete --refresh-cache

        # set app
        export HEROKU_APP=meetup-bot-bot

        # ubuntu 22.*
        heroku stack:set heroku-22

        # programmatically add .env vars to heroku config vars
        cat .env | tr '\n' ' ' | xargs heroku config:set -a meetup-bot-bot
        ```
      * Container manifest
        * See [heroku.yml](heroku.yml)
        * Creates a container from [Dockerfile.prod](Dockerfile.prod), attaches Redis and scheduler
      * Usage
        ```bash
        # deploy container via heroku.yml
        heroku create meetup-bot-bot --manifest

        # setup python buildpack
        heroku buildpacks:add heroku/python

        # add a web worker
        heroku ps:scale web=1                                           # stop dymo via `web=0`

        # destroy app
        heroku apps:destroy -a meetup-bot-bot --confirm meetup-bot-bot
        ```
      * TODO: document scheduler w/API commands
* gitleaks
  * git pre-commit hook
    ```bash
    git config hooks.gitleaks true
    ```
  * CI/CD
    * See `meetup_bot/.github/workflows/main.yml`
  * Manual run
    ```bash
    # set env vars
    export GITLEAKS_CONFIG=$(pwd)/gitleaks.toml         # precedence: --config, env var, --source, default config
    export GITLEAKS_REPORT=$(pwd)/gitleaks_report.json

    # bash completion
    gitleaks completion bash >> ~/.gitleaks.bash
    echo ". ~/.gitleaks.bash" >> ~/.bashrc

    # scan local directories for secrets
    gitleaks detect --no-git

    # run w/report
    gitleaks detect -r $GITLEAKS_REPORT                 # generate json report (default)
    ```

## TODO
* ~~Third-party Meetup lookup~~
  * ~~If API only covers org events, use something like [Playwright](https://playwright.dev/python/) to scrape outstanding events~~
* ~~Refresh token~~
  * ~~Schedule `gen_token.py` every 55 minutes (3300s)~~
* FastAPI
  * ~~endpoints~~
    * ~~Meetup query~~
    * Slack bot: POST formatted messages to Slack channels `#okc-metro` && `#events`
      * `#testingchannel` is the canary and works swimmingly
* Schedule event posts in channels
  * Methods
    * ~~launchd~~
    * ~~cron~~
    * ~~k8s cron~~
    * ~~jupyter~~
    * ~~aws lambda~~
    * [scheduler](https://devcenter.heroku.com/articles/scheduler): built-in heroku addon
      * deploy > document
  * Time Frame 
    * 3 days before
    * 2 hours before
* ~~Docker/Docker-Compose~~
  * ~~Mitigates pain of Poetry virtual environments~~
  * ~~Can migrate to prod VPS and/or k8s~~
* Lock down endpoints in prod / general hardening
* Documentation

## Stretch Goals
* JWT instead of OAuth2
  * May be able to do away with Playwright re: manual authorization via creds + requests
* Slash commands to manually call:
  * Next `n` events
  * This week's events
  * Create new events

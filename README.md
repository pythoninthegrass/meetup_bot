<img alt="gitleaks badge" src="https://img.shields.io/badge/protected%20by-gitleaks-blue">

# meetup_bot
**Table of Contents**
* [meetup_bot](#meetup_bot)
  * [Summary](#summary)
  * [Usage](#usage)
  * [TODO](#todo)
  * [Stretch Goals](#stretch-goals)
  * [Further Reading](#further-reading)

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

        # config vars
        heroku config

        # stack
        heroku stack

        # ubuntu 22.* buildpack
        # heroku stack:set heroku-22

        # custom container via manifest
        heroku stack:set container

        # programmatically add .env vars to heroku config vars
        cat .env | tr '\n' ' ' | xargs heroku config:set -a meetup-bot-bot
        ```
      * Container manifest
        * See [heroku.yml](heroku.yml)
        * Creates a container from [Dockerfile.web](Dockerfile.web), attaches Redis and scheduler
      * Container registry
        * Faster than CI builds triggered by GitHub commits
        ```bash
        # login
        heroku container:login

        # heroku wrapper build (w/cache)
        heroku container:push web

        # docker buildx (arm)
        export TAG="registry.heroku.com/meetup-bot-bot/web:latest"
        docker buildx build -f Dockerfile.web --progress=plain -t $TAG --load .
        docker push registry.heroku.com/meetup-bot-bot/web

        # release image to app
        heroku container:release web

        # exec/ssh into container
        heroku ps:exec

        # open website
        heroku open
        ```
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
* JSON Web Token (JWT) Auth Flow
  * Use JWT vs. OAuth2 flow
    * Latter needs manual intervention/user spoofing/captcha bypass
  * ~~Format payload, headers, and sign JWT~~
  * ~~Successful POST (200) to OAuth URL~~
  * Extract `access_token` and `refresh_token` from response
    * Getting raw HTML of a page vs. JSON payload 🤔
* FastAPI
  * ~~endpoints~~
    * ~~Meetup query~~
    * Slack bot: POST formatted messages to Slack channels `#okc-metro` && `#events`
      * `#testingchannel` is the canary and works swimmingly
* Makefile
  * `docker buildx` && heroku push/release image
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

## Further Reading
[API Doc Authentication | Meetup](https://www.meetup.com/api/authentication/#p04-jwt-flow-section)

[How to Handle JWTs in Python](https://auth0.com/blog/how-to-handle-jwt-in-python/)

[Usage Examples — PyJWT 2.4.0 documentation](https://pyjwt.readthedocs.io/en/stable/usage.html#encoding-decoding-tokens-with-rs256-rsa)

[Building a Basic Authorization Server using Authorization Code Flow (PKCE) | by Ratros Y. | Medium](https://medium.com/@ratrosy/building-a-basic-authorization-server-using-authorization-code-flow-pkce-3155e843466)


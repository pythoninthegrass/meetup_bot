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
    # install httpie
    brew update
    brew install httpie

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

        # move to git repo
        cd meetup-bot-bot/

        # set app
        export HEROKU_APP=meetup-bot-bot

        # config vars
        heroku config

        # stack
        heroku stack

        # ubuntu 22.* buildpack
        # heroku stack:set heroku-22

        # set heroku git to app
        heroku git:remote -a $HEROKU_APP

        # custom container via manifest
        heroku stack:set container

        # programmatically add .env vars to heroku config vars
        cat .env | tr '\n' ' ' | xargs heroku config:set -a $HEROKU_APP

        # deploy to heroku
        git push heroku main

        # watch logs (build, server activity)
        heroku logs --tail

        # test image locally
        docker pull registry.heroku.com/meetup-bot-bot/web
        docker run --rm -it registry.heroku.com/meetup-bot-bot/web bash

        # control remote builds (e.g., CI)
        heroku plugins:install heroku-builds

        # get all builds
        # * NOTE: append `-a $HEROKU_APP` if env var isn't set
        heroku builds

        # cancel specific build
        λ heroku builds:cancel fd8ee600-46d8-4f2c-99e9-b77c109ba431
        Stopping build fd8ee600-46d8-4f2c-99e9-b77c109ba431... done

        # cancel latest build
        heroku builds:cancel
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

        # pull buildx image (on remote intel box)
        docker pull moby/buildkit:buildx-stable-1

        # create builder
        docker buildx create \
        --name amd64_builder \
        --node linux_amd64_builder \
        --platform linux/amd64 \
        ssh://USERNAME@IP_ADDRESS_OF_BUILDER

        # select new builder
        docker buildx use amd64_builder

        # build intel image
        docker buildx build -f Dockerfile.web --progress=plain -t $TAG --load .

        # push to heroku registry
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
        heroku apps:destroy -a meetup-bot-bot --confirm $HEROKU_APP
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
* FastAPI
    * Slack bot: POST formatted messages to Slack channels `#okc-metro` && `#events`
      * `#testingchannel` is the canary and works swimmingly
* Schedule event posts in channels
  * Methods
    * ~~[scheduler](https://devcenter.heroku.com/articles/scheduler): built-in heroku addon~~
  * Time Frame 
    * Currently scheduled for 10am/6pm cst (1500/2300 utc)
* Documentation

## Stretch Goals
* Indicate online vs. in-person
* Time Frame 
  * 3 days before
  * 2 hours before
* Slash commands to manually call:
  * Next `n` events
  * This week's events
  * Create new events

## Further Reading
[API Doc Authentication | Meetup](https://www.meetup.com/api/authentication/#p04-jwt-flow-section)

[How to Handle JWTs in Python](https://auth0.com/blog/how-to-handle-jwt-in-python/)

[Building a Basic Authorization Server using Authorization Code Flow (PKCE) | by Ratros Y. | Medium](https://medium.com/@ratrosy/building-a-basic-authorization-server-using-authorization-code-flow-pkce-3155e843466)

[How to cancel a Heroku build | remarkablemark](https://remarkablemark.org/blog/2021/05/05/heroku-cancel-build/)

[OAuth2 with Password (and hashing), Bearer with JWT tokens - FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)

[Python bcrypt - hashing passwords in Python with bcrypt](https://zetcode.com/python/bcrypt/)

[MushroomMaula/fastapi_login](https://github.com/MushroomMaula/fastapi_login)

[FastAPI Auth + Login Page](https://dev.to/athulcajay/fastapi-auth-login-page-48po)

[checkbashisms](https://command-not-found.com/checkbashisms)

<img alt="gitleaks badge" src="https://img.shields.io/badge/protected%20by-gitleaks-blue">

# meetup_bot
**Table of Contents**
* [meetup\_bot](#meetup_bot)
  * [Summary](#summary)
  * [Minimum Requirements](#minimum-requirements)
  * [Recommended Requirements](#recommended-requirements)
  * [Quickstart](#quickstart)
    * [Python only](#python-only)
    * [Shell wrapper](#shell-wrapper)
    * [Devbox](#devbox)
    * [Docker](#docker)
    * [Docker Compose](#docker-compose)
  * [TODO](#todo)
  * [Stretch Goals](#stretch-goals)
  * [Further Reading](#further-reading)

## Summary
Use Meetup Pro API to send Slack messages before events occur.

## Minimum Requirements
* [Python 3.11.6](https://www.python.org/downloads/)
* [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
* [Create a Meetup API key](https://secure.meetup.com/meetup_api/key/)
* Slack
  * [Create a Slack app](https://api.slack.com/apps)
  * [Create a Slack bot](https://api.slack.com/bot-users)

## Recommended Requirements
* [Devbox](https://www.jetpack.io/devbox/docs/quickstart/)
* [Docker](https://www.docker.com/products/docker-desktop)

## Quickstart
* Clone repo
* Copy `.env.example` to `.env` and fill out environment variables

### Python only
```bash
cd ./app

# run individual app
python <sign_jwt|meetup_query|slackbot|main>.py

# run only main app
python main.py
```

### Shell wrapper
```bash
cd ./app

# standalone server w/hard-coded port (default: 3000)
./startup.sh

# standalone server w/port argument
./startup.sh 3000

# server used with scheduled job (e.g., cron job)
./scheduler.sh
```

### Devbox
I.e., [Nix Package Manager](https://search.nixos.org/packages)
```bash
# enter dev environment
devbox shell

# run individual app
python <sign_jwt|meetup_query|slackbot|main>.py

# exit dev environment
exit

# run standalone server
devbox run start

# run tests
devbox run test
```

### Docker
```bash
cd ./app

# build image
docker build -f Dockerfile.web --progress=plain -t meetup_bot:latest .

# run image
docker run --name meetup_bot -it --rm --env-file .env -p 3000:3000 meetup_bot bash
```

### Docker Compose
```bash
cd ./app

# build image
docker-compose build --remove-orphans

# run image
docker-compose up -d

# enter server container
docker exec -it meetup_bot-cont bash

# exit server container
exit

# stop image
docker-compose stop

# remove image
docker-compose down --volumes
```

## TODO
* Norman events
  * Get Norman events from existing GraphQL API
    * Coded as `Oklahoma City`
    * Will need to modify the query to get title and body content
  * Post to `#norman`
    * M-F
* FastAPI
  * Store auth in browser session vs. memory
* Unit test
  * Add badge
  * 100% coverage
* Documentation
  * quickstart
    * ~~Docker Compose~~
    * `taskfile` usage
    * `devbox` usage
    * QA (especially accounts)
  * Coralogix logging
  * healthchecks.io

## Stretch Goals
* Indicate online vs. in-person
* Time Frame 
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

[Efficient Python Docker Image from any Poetry Project](https://denisbrogg.hashnode.dev/efficient-python-docker-image-from-any-poetry-project)

[Document docker poetry best practices · python-poetry · Discussion #1879](https://github.com/python-poetry/poetry/discussions/1879#discussioncomment-216865)

[Building Docker images in Kubernetes | Snyk](https://snyk.io/blog/building-docker-images-kubernetes/)

[Kaniko, How to Build Container Image with SSH | by Yossi Cohn | HiredScore Engineering | Medium](https://medium.com/hiredscore-engineering/kaniko-builds-with-private-repository-634d5e7fa4a5)

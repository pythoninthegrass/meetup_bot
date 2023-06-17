<img alt="gitleaks badge" src="https://img.shields.io/badge/protected%20by-gitleaks-blue">

# meetup_bot
**Table of Contents**
* [meetup\_bot](#meetup_bot)
  * [Summary](#summary)
  * [TODO](#todo)
  * [Stretch Goals](#stretch-goals)
  * [Further Reading](#further-reading)

## Summary
Use Meetup Pro API to send Slack messages before events occur.


## TODO
* FastAPI
    * Store auth in browser session vs. memory
* Unit test
  * Add badge
  * 100% coverage
* Documentation
  * quickstart
    * `justfile` usage
    * ~~move usage: dev/prod to docs subdir~~ [wiki](https://github.com/pythoninthegrass/meetup_bot/wiki)
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

[Building Docker images in Kubernetes | Snyk](https://snyk.io/blog/building-docker-images-kubernetes/)

[Kaniko, How to Build Container Image with SSH | by Yossi Cohn | HiredScore Engineering | Medium](https://medium.com/hiredscore-engineering/kaniko-builds-with-private-repository-634d5e7fa4a5)

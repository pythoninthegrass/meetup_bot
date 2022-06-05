# meetup_bot

## Summary
Use Meetup Pro API to send Slack messages before events occur.

## TODO
* Third-party Meetup lookup
  * If API only covers org events, use something like [Playwright](https://playwright.dev/python/) to scrape outstanding events
* POST formatted messages to Slack channels `#okc-metro` && `#events`
* Docker/Docker-Compose
  * Mitigates pain of Poetry virtual environments
  * Can migrate to prod VPS and/or k8s 
* Schedule event posts in ___ channels
  * Methods
    * launchd
    * cron
    * k8s cron
    * jupyter
    * aws lambda
  * Time Frame 
    * 3 days before
    * 2 hours before
* Refresh token
  * Schedule `gen_token.py` every 55 minutes (3300s)
* Documentation

## Stretch Goals
* JWT instead of OAuth2
  * May be able to do away with Playwright re: manual authorization via creds + requests
* Slash commands to manually call:
  * Next `n` events
  * This week's events
  * Create new events

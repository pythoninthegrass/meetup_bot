# meetup_bot

## Summary
Use Meetup Pro API to send Slack messages before events occur.

## TODO
* ~~Fix Slack POST to mirror curl command (latter's working)~~ ✔️
  * ~~Integrate or abandon `knockknock` vs. `requests`~~ [**EDIT**: went the requests route] ✔️
* GraphQL + Meetup Pro API
  * `requests`
    * GET equivalent for Techlahoma user groups ✔️
* Third-party Meetup lookup
  * If API only covers org events, use something like [Playwright](https://playwright.dev/python/) to scrape outstanding events
* ~~Find out Kimberly's manual process~~ ✔️
* Refactor token/refresh generation with `authlib`
* Redirect to httpbin
  * Pending additional OAuth client (5/9/2022)
  * May be able to do away with Playwright re: manual authorization via creds 
* Format GraphQL output
* POST formatted messages to Slack channels `#okc-metro` && `#events`
* Schedule event posts in ___ channels
  * 3 days before
  * 2 hours before

## Stretch Goals
* Slash commands to manually call:
  * Next `n` events
  * This week's events
  * Create new events

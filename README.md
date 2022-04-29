# meetup_bot

## Summary
Use Meetup Pro API to send Slack messages before events occur.

## TODO
* Fix Slack POST to mirror curl command (latter's working)
  * Integrate or abandon `knockknock` vs. `requests`
* GraphQL + Meetup Pro API
  * `strawberry` [library](https://strawberry.rocks/)
    * May just be a _server_ and not a _client_ for GraphQL
  * `requests`
    * GET equivalent for Techlahoma user groups
* Third-party Meetup lookup
  * If API only covers org events, use something like [Playwright](https://playwright.dev/python/) to scrape outstanding events
* Find out Kimberly's manual process
* Slash commands to manually call:
  * Next `n` events
  * This week's events
* Schedule event posts in ___ channels
  * 3 days before
  * 2 hours before

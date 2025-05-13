# TODO

* Refactor authentication
  * passlib + bcrypt -> bcrypt (see: [AttributeError: module 'bcrypt' has no attribute '__about__' with new 4.1.1 version · Issue #684 · pyca/bcrypt](https://github.com/pyca/bcrypt/issues/684#issuecomment-1902590553))
  * Secured endpoints
    * Store auth in browser session vs. memory
* Scheduling
  * Couple scheduling with locations (e.g., Norman vs. OKC)
* Norman events
  * Get Norman events from existing GraphQL API
    * Coded as `Oklahoma City`
    * Will need to modify the query to get title and body content
  * Post to `#norman`
    * M-F
* Unit test
  * Add badge
  * 100% coverage
* Documentation
  * quickstart
    * `taskfile` usage
    * QA (especially accounts)
  * Coralogix logging

## Stretch Goals

* Indicate online vs. in-person
* Time Frame 
  * 2 hours before
* Slash commands to manually call:
  * Next `n` events
  * This week's events
  * Create new events

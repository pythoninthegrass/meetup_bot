# TODO

* Move exclusions to either
  * GraphQL
  * Filter by url (e.g., `https://www.meetup.com/project3810/events/308160679/`)
* Convert code base to golang
* Refactor authentication
  * Store auth in browser session vs. memory
* Scheduling
  * Couple scheduling with locations (e.g., Norman vs. OKC)
* Norman events
  * Get Norman events from existing GraphQL API
    * Coded as `Oklahoma City`
    * Will need to modify the query to get title and body content
  * Post to `#norman`
    * M-F

## Stretch Goals

* Indicate online vs. in-person
* Time Frame 
  * 2 hours before
* Slash commands to manually call:
  * Next `n` events
  * This week's events
  * Create new events

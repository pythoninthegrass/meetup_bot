<img alt="gitleaks badge" src="https://img.shields.io/badge/protected%20by-gitleaks-blue">

# meetup_bot

## Summary
Use Meetup Pro API to send Slack messages before events occur.

## Usage
* meetup_bot
  * TODO
* gitleaks
  * git pre-commit hook
    ```bash
    git config hooks.gitleaks true
    ```
  * CI/CD
    * TODO
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
    * launchd
    * cron
    * k8s cron
    * jupyter
    * aws lambda
  * Time Frame 
    * 3 days before
    * 2 hours before
* ~~Docker/Docker-Compose~~
  * ~~Mitigates pain of Poetry virtual environments~~
  * ~~Can migrate to prod VPS and/or k8s~~
* Documentation

## Stretch Goals
* JWT instead of OAuth2
  * May be able to do away with Playwright re: manual authorization via creds + requests
* Slash commands to manually call:
  * Next `n` events
  * This week's events
  * Create new events

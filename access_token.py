#!/usr/bin/env python3

from gen_url import *
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)    # TODO: set to True
    context = browser.new_context()
    page = context.new_page()
    # page.goto("https://techlahoma-peekahead.netlify.app/?code=9b45c9cf293e66fc21303c0ea49a4082")
    page.goto(url)
    with page.expect_navigation():
        page.locator("#login").click()
    page.locator("[data-testid=email]").click()
    page.locator("[data-testid=email]").fill("user@gmail.com")
    page.locator("[data-testid=current-password]").click()
    page.locator("[data-testid=current-password]").fill("abc123")

    # TODO: get `CODE` from page.url

    context.close()
    browser.close()


if __name__ == "__main__":
    print("Access the URL below, authorize the application, and get the code that appears on the URL")
    print(url)  # TODO: QA -- imports from gen_url.py

    with sync_playwright() as playwright:
        run(playwright)

    # CODE = input('Enter the code: ')
    info = get_token_info(MEETUP_KEY, MEETUP_SECRET, REDIRECT_URI, CODE)

    print("***** access_token *****")
    print(json.dumps(info, sort_keys=True, indent=4))

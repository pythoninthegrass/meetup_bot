#!/usr/bin/env python3

import pandas as pd
# import re
from icecream import ic
# from pathlib import Path
from playwright.sync_api import Playwright, sync_playwright, expect

"""
Due to Meetup's GraphQL schema, third-party groups are not exposed in the API.

Works around that by scraping the HTML of the groups page and extracting the group name (urlname).
"""

# verbose icecream
ic.configureOutput(includeContext=True)

# scrape the url for subdomain (i.e., 'okc-fp')
# https://www.meetup.com/okc-fp/
# url = "https://www.meetup.com/find/?suggested=true&source=GROUPS&keywords=programming&categoryId=546&distance=tenMiles&location=us--ok--Oklahoma%20City"
# url = "https://www.meetup.com/find/"
url = "https://www.meetup.com/find/?distance=tenMiles&source=GROUPS&categoryId=546"


def run(playwright: Playwright) -> None:
    """
    Open URL, scrape for subdomain, and save to CSV.

    Due to JSHandler type, have to export to CSV, import, then split at the second to last '/' to get the 'urlname' field.
    """

    # open browser
    browser = playwright.chromium.launch(headless=True)

    # give OKC location and allow geolocation to be used
    context = browser.new_context(
        geolocation={"latitude": 35.467560, "longitude": -97.516426},
        permissions=["geolocation"],
    )

    # Open new page
    page = context.new_page()

    # Go to https://www.meetup.com/find/
    page.goto(url)

    # Click [placeholder="Enter location"]
    # page.locator("[placeholder=\"Enter location\"]").click()

    # Fill [placeholder="Enter location"]
    # page.locator("[placeholder=\"Enter location\"]").fill("oklahoma city")

    # Click text=Oklahoma City, Oklahoma, USA
    # page.locator("text=Oklahoma City, Oklahoma, USA").click()

    # expect(page).to_have_url("https://www.meetup.com/find/?location=us--ok--Oklahoma%20City&source=EVENTS")

    # Click [placeholder="Search for keywords"]
    # page.locator("[placeholder=\"Search for keywords\"]").click()

    # Fill [placeholder="Search for keywords"]
    # page.locator("[placeholder=\"Search for keywords\"]").fill("programming")

    # Click text=Any distanceicon
    # page.locator("text=Any distanceicon").click()

    # Click text=10 miles
    # page.locator("text=10 miles").click()
    # expect(page).to_have_url("https://www.meetup.com/find/?location=us--ok--Oklahoma%20City&source=EVENTS&distance=tenMiles")

    # Click text=Any categoryicon
    # page.locator("text=Any categoryicon").click()

    # Click text=Technology
    # page.locator("text=Technology").click()
    # expect(page).to_have_url("https://www.meetup.com/find/?location=us--ok--Oklahoma%20City&source=EVENTS&distance=tenMiles&categoryId=546")

    # Click [data-testid="GROUPS"]
    # page.locator("[data-testid=\"GROUPS\"]").click()
    # expect(page).to_have_url("https://www.meetup.com/find/?location=us--ok--Oklahoma%20City&source=GROUPS&distance=tenMiles&categoryId=546")

    # xpath
    # //*[@id="group-card-in-search-results"]

    # regex = re.compile(r'"https:\/\/www\.meetup\.com\/(.*?)\/"')

    handles = []

    # loop through each group and get href from id="group-card-in-search-results"
    for group in page.query_selector_all("#group-card-in-search-results"):
        handle = group.get_property("href")
        handles.append(handle)

    context.close()
    browser.close()

    # URLs only
    # for i in handles:
    #     print(i)

    # dataframe of URLs
    df = pd.DataFrame(handles)
    df.columns = ["url"]

    # export raw CSV
    df.to_csv("raw/groups.csv", index=False)

    # read groups.csv
    df = pd.read_csv("raw/groups.csv")

    # add column for urlname (group name) (split at second to last field)
    df["urlname"] = df["url"].apply(lambda x: x.split("/")[-2])

    # export final CSV
    df.to_csv("raw/groups.csv", index=False)


with sync_playwright() as playwright:
    run(playwright)

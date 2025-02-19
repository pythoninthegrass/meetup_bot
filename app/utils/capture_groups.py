#!/usr/bin/env python3

import pandas as pd
from icecream import ic
from playwright.sync_api import Playwright, sync_playwright

"""
Due to Meetup's GraphQL schema, third-party groups are not exposed in the API.

Works around that by scraping the HTML of the groups page and extracting the group name (urlname).
"""

# verbose icecream
ic.configureOutput(includeContext=True)

# pandas don't truncate output
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)

# scrape the url for subdomain (i.e., 'okc-fp')
base_url = "https://www.meetup.com"
# * # anyDistance (default), twoMiles, fiveMiles, tenMiles, twentyFiveMiles, fiftyMiles, hundredMiles
distance = "tenMiles"
source = "GROUPS"                       # EVENTS (default), GROUPS
category_id = "546"                     # technology groups
location = "us--ok--Oklahoma%20City"    # OKC

url = base_url + "/find/?distance=" + distance + "&source=" + source + "&categoryId=" + category_id + "&location=" + location


# TODO: skip groups that are a part of the Techlahoma Foundation
def run(playwright: Playwright) -> None:
    """
    Open URL, scrape for subdomain, and save to CSV.

    Due to JSHandler type, have to export to CSV, import, then split at the second to last '/' to get the 'urlname' field.
    """

    # ! run `poetry run playwright install chromium` first

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

    # xpath
    # //*[@id="group-card-in-search-results"]

    handles = []

    # loop through each group and get href from id="group-card-in-search-results"
    handles = [group.get_property("href") for group in page.query_selector_all("#group-card-in-search-results")]

    # page.pause()    # pause for debugging

    context.close()
    browser.close()

    return handles


def process(handles):
    """
    Process handles (list of JSHandle objects) and save to CSV.
    """

    # exclusions
    exclusions = [
        "oklahoma-city-servicenow-development-meetup",
        "oklahoma-clean-technology-association",
        "reddirtbitcoiners",
    ]

    # convert jshandle to string
    handles = [str(handle) for handle in handles]

    # remove exclusions (get subdirectory)
    handles = [handle for handle in handles if handle.split("/")[-2] not in exclusions]

    # dataframe of URLs
    df = pd.DataFrame(handles)
    df.columns = ["url"]
    ic(df.head(df.shape[0]))

    # export raw CSV
    df.to_csv("../raw/scratch.csv", index=False)

    # read groups.csv
    df = pd.read_csv("../raw/scratch.csv")

    # add column for urlname (group name) (split at second to last field)
    df["urlname"] = df["url"].apply(lambda x: x.split("/")[-2])

    # sort by urlname
    df = df.sort_values(by=["urlname"])

    # export final CSV
    df.to_csv("../groups.csv", index=False)


def main():
    # scrape
    with sync_playwright() as playwright:
        handles = run(playwright)

    # process
    process(handles)


if __name__ == "__main__":
    main()

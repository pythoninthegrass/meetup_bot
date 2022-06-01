#!/usr/bin/env python3

# SOURCE: https://gist.github.com/valeriocos/e16424bc7dc0f2d6dd8bb9295c6f9a4b

import requests
from icecream import ic
# from pathlib import Path

# verbose icecream
ic.configureOutput(includeContext=True)

"""
Useful open GraphQL API to test syntax
"""

query = """query {
    characters {
    results {
      name
      status
      species
      type
      gender
    }
  }
}"""

url = 'https://rickandmortyapi.com/graphql/'
r = requests.post(url, json={'query': query})
ic(r.status_code)
ic(r.text)

"""Check which companies in the universe are available on Trading 212.

Run this on your own computer, once, and again whenever you like:

    1. In the Trading 212 app: Settings -> API, generate a key with the
       "metadata" permission ONLY. Do not grant trading or withdrawal access.
    2. In a terminal, from this folder:
         export T212_API_KEY="your key"
         export T212_API_SECRET="your secret"   # if your key came with one
         python check_trading212.py
    3. Commit data/trading212.csv (it holds only tickers and yes/no).

Never put your key in a file, a commit, or a chat. It stays in your terminal.

The API allows one request to this endpoint every 50 seconds, and this script
makes exactly one.
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

from scorecard.data import load_universe
from scorecard.trading212 import AVAILABILITY_FILE, match_instruments

URL = "https://live.trading212.com/api/v0/equity/metadata/instruments"


def fetch_instruments(key: str, secret: str | None) -> list[dict]:
    if secret:
        auth = "Basic " + base64.b64encode(f"{key}:{secret}".encode()).decode()
    else:
        auth = key
    req = urllib.request.Request(URL, headers={"Authorization": auth, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def main() -> None:
    key = os.environ.get("T212_API_KEY")
    if not key:
        sys.exit("Set T212_API_KEY first (see the instructions at the top of this file).")
    try:
        instruments = fetch_instruments(key, os.environ.get("T212_API_SECRET"))
    except urllib.error.HTTPError as e:
        hints = {401: "the key was rejected; check it and the secret",
                 403: "the key needs the 'metadata' permission",
                 429: "rate limited; wait a minute and try again"}
        sys.exit(f"Trading 212 returned {e.code}: {hints.get(e.code, e.reason)}")

    result = match_instruments(load_universe(), instruments)
    result["checked_on"] = date.today().isoformat()
    result.to_csv(AVAILABILITY_FILE, index=False)
    missing = result[result.available == "no"]
    print(f"{len(instruments)} instruments fetched. {len(result) - len(missing)} of {len(result)} companies available.")
    if len(missing):
        print("Not found (check these by hand in the app before trusting a 'no'):")
        for r in missing.itertuples():
            print(f"  {r.name} ({r.ticker})")
    print(f"Saved {AVAILABILITY_FILE.relative_to(AVAILABILITY_FILE.parent.parent)}")


if __name__ == "__main__":
    main()

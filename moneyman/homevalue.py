"""OPTIONAL, OPT-IN online home-value lookup.

⚠️  This is the ONLY part of MoneyMan that can touch the internet, and it does so
ONLY when you explicitly turn it on (Look up home value online? = y in My-Profile.csv).

What it sends:  ONLY the street address you typed.
What it never sends:  your balances, transactions, debts, or any financial detail.

How it works:
  * If you provide a free property-data API key (set the environment variable
    MONEYMAN_RENTCAST_KEY, e.g. a free RentCast key), MoneyMan asks that service
    for an estimated value, sending only the address.
  * If you don't provide a key, MoneyMan does NOT fetch anything. It just builds a
    Zillow/Redfin search link you can click to read the value and type it into your
    profile — so even then, nothing is sent automatically.

If you want to stay 100% offline, set "Look up home value online?" to n (the
default) and just type your home value into My-Profile.csv.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request


def zillow_link(address: str) -> str:
    return "https://www.zillow.com/homes/" + urllib.parse.quote(address) + "_rb/"


def redfin_link(address: str) -> str:
    return "https://www.redfin.com/stingray/do/location-autocomplete?location=" \
        + urllib.parse.quote(address)


def estimate(address: str, api_key: str | None = None, timeout: int = 8) -> dict:
    """Return {value, source, link, note}. Only the address is ever transmitted."""
    address = (address or "").strip()
    result = {"value": None, "source": "none", "link": zillow_link(address),
              "note": ""}
    if not address:
        result["note"] = "No address provided."
        return result

    api_key = api_key or os.environ.get("MONEYMAN_RENTCAST_KEY")
    if not api_key:
        result["note"] = ("No property-API key set, so nothing was sent online. "
                          "Open the link to read your home's value and type it into "
                          "My-Profile.csv. (To enable automatic lookup, set a free "
                          "RentCast key in the MONEYMAN_RENTCAST_KEY environment "
                          "variable.)")
        return result

    # Address-only request to a property valuation API.
    url = ("https://api.rentcast.io/v1/avm/value?address="
           + urllib.parse.quote(address))
    req = urllib.request.Request(url, headers={
        "X-Api-Key": api_key, "Accept": "application/json",
        "User-Agent": "MoneyMan/1.0 (local, offline finance tool)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        value = data.get("price") or data.get("value") or data.get("priceRangeLow")
        if value:
            result.update(value=round(float(value), 2), source="online estimate",
                          note="Estimated from a property-data service (address only "
                               "was sent).")
        else:
            result["note"] = "The service returned no value for this address."
    except Exception as e:                            # never crash the whole report
        result["note"] = (f"Online lookup failed ({type(e).__name__}); nothing "
                          "sensitive was exposed. Enter the value manually instead.")
    return result

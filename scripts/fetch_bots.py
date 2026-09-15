"""
Fetch the current list of bot-flagged Wikipedia usernames.

Usage:
    python fetch_bots.py --out data/bot_usernames.json
"""

import argparse
import json
import requests

API_URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": "wikipedia-conflict-sensor/0.1 (research project; contact: youremail@example.com)"
}


def fetch_bot_usernames() -> list[str]:
    """Return every username currently in the 'bot' user group."""
    usernames = []
    params = {
        "action": "query",
        "format": "json",
        "list": "allusers",
        "augroup": "bot",
        "aulimit": "max",
        "formatversion": "2",
    }

    while True:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        users = data.get("query", {}).get("allusers", [])
        usernames.extend(u["name"] for u in users)

        if "continue" in data:
            params.update(data["continue"])
        else:
            break

    return usernames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Output JSON path")
    args = parser.parse_args()

    bots = fetch_bot_usernames()
    print(f"Found {len(bots)} bot-flagged accounts.")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(bots, f, ensure_ascii=False, indent=2)

    print(f"Saved to {args.out}")


if __name__ == "__main__":
    main()
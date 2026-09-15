"""
Pull the full revision history for a Wikipedia article via the MediaWiki API.

Usage:
    python fetch_revisions.py "Kyle Rittenhouse" --out data/rittenhouse_revisions.json
"""

import argparse
import json
import time
import requests

API_URL = "https://en.wikipedia.org/w/api.php"

# Fields pulled per revision. See:
# https://www.mediawiki.org/wiki/API:Revisions
RVPROPS = [
    "ids",        # revision id, parent id
    "timestamp",
    "user",       # editor username or IP
    "userid",     # 0 for anonymous/IP editors
    "size",       # bytes after this edit -> lets you compute size_change yourself
    "comment",    # edit summary (needed for revert-comment heuristics)
    "flags",      # gives you 'minor' flag
    "tags",       # includes things like 'mw-rollback', 'mw-undo' -> a much more
                  # reliable revert signal than comment-pattern matching alone
]

HEADERS = {
    # Wikipedia asks for a descriptive User-Agent identifying the tool/contact.
    # Replace the email with your own before running at scale.
    "User-Agent": "wikipedia-conflict-sensor/0.1 (research project; contact: jovisha2275@gmail.com)"
}


def fetch_all_revisions(title: str, sleep: float = 0.2) -> list[dict]:
    """Fetch the complete revision history for a single article, oldest to newest."""
    revisions = []
    params = {
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "titles": title,
        "rvprop": "|".join(RVPROPS),
        "rvslots": "main",
        "rvlimit": "max",       # 500 per request for non-bot accounts
        "rvdir": "newer",       # walk forward from article creation
        "formatversion": "2",
    }

    while True:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        pages = data.get("query", {}).get("pages", [])
        if not pages:
            break
        page = pages[0]
        if "missing" in page:
            raise ValueError(f"Article '{title}' not found.")

        batch = page.get("revisions", [])
        revisions.extend(batch)

        # Pagination: MediaWiki returns a 'continue' block when there's more.
        if "continue" in data:
            params["rvcontinue"] = data["continue"]["rvcontinue"]
            time.sleep(sleep)  # be polite to the API
        else:
            break

    return revisions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title", help="Exact Wikipedia article title, e.g. 'Kyle Rittenhouse'")
    parser.add_argument("--out", required=True, help="Output JSON path")
    args = parser.parse_args()

    print(f"Fetching revision history for: {args.title}")
    revisions = fetch_all_revisions(args.title)
    print(f"Pulled {len(revisions)} revisions.")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(revisions, f, ensure_ascii=False, indent=2)

    print(f"Saved to {args.out}")


if __name__ == "__main__":
    main()
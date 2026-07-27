import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

TABLE_URL = f"{SUPABASE_URL}/rest/v1/ranking_leaderboard"


def request(method, path_and_query, body=None, prefer=None):
    url = f"{TABLE_URL}{path_and_query}"
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer

    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url} -> {e.code}: {e.read().decode()}")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def run_sync():
    if not SUPABASE_URL or not SERVICE_ROLE_KEY:
        print("Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY env vars.")
        sys.exit(1)

    with open("polish_top.json", "r", encoding="utf-8") as f:
        players = json.load(f)

    if not isinstance(players, list) or len(players) == 0:
        print("Empty or invalid player list, skipping sync.")
        sys.exit(1)

    fetched_names = set()
    upserted = 0
    inserted = 0
    failed = 0

    for player in players:
        name = (player.get("name") or "").strip()
        rank = player.get("rank")

        if not name or not isinstance(rank, int):
            continue

        fetched_names.add(name)

        try:
            existing = request("GET", f"?select=id&name=eq.{urllib.parse.quote(name)}")
            if existing:
                row_id = existing[0]["id"]
                request(
                    "PATCH",
                    f"?id=eq.{row_id}",
                    body={
                        "leaderboard_rank": rank,
                        "is_official_leaderboard": True,
                        "updated_at": now_iso(),
                    },
                    prefer="return=minimal",
                )
                upserted += 1
            else:
                request(
                    "POST",
                    "",
                    body={
                        "name": name,
                        "leaderboard_rank": rank,
                        "is_official_leaderboard": True,
                        "steam_id": None,
                    },
                    prefer="return=minimal",
                )
                inserted += 1
        except RuntimeError as e:
            failed += 1
            print(f"Failed to upsert '{name}': {e}")

    # Cleanup: official entries no longer in the fetched list lose their rank
    # (dropped out of the top 5000) rather than being deleted.
    stale_entries = request("GET", "?select=id,name&is_official_leaderboard=eq.true") or []
    cleaned = 0
    for entry in stale_entries:
        if entry["name"] not in fetched_names:
            try:
                request(
                    "PATCH",
                    f"?id=eq.{entry['id']}",
                    body={"leaderboard_rank": None, "updated_at": now_iso()},
                    prefer="return=minimal",
                )
                cleaned += 1
            except RuntimeError as e:
                print(f"Failed to clear stale entry '{entry['name']}': {e}")

    print(
        "Summary:",
        json.dumps(
            {
                "total_in_json": len(players),
                "upserted": upserted,
                "inserted": inserted,
                "failed": failed,
                "cleaned": cleaned,
            }
        ),
    )


if __name__ == "__main__":
    run_sync()

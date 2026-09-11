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

    # Deduplicate by name BEFORE syncing anything: two different accounts
    # (e.g. a smurf/alt) can share the same display name on Valve's
    # leaderboard. Without this, the upsert loop below would process both
    # under the same `name` key and whichever one runs last silently
    # overwrites the other's row via PATCH — effectively random which
    # rank "wins". Keep only the best (lowest) rank per name up front.
    best_by_name = {}
    for player in players:
        name = (player.get("name") or "").strip()
        rank = player.get("rank")
        if not name or not isinstance(rank, int):
            continue
        if name not in best_by_name or rank < best_by_name[name]["rank"]:
            best_by_name[name] = player

    players = list(best_by_name.values())

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

    # Cleanup: official (top-5000-only) entries no longer in the fetched list
    # fall into two cases, handled differently:
    #
    # - No steam_id: this row exists ONLY because of this scraper, so once
    #   it drops out of the fetched list (inactivity, or a rename — matched
    #   by name too, so a rename has the same effect) there's no reason to
    #   keep it around at all. Delete outright.
    #
    # - Has steam_id: the player also joined the site's own ranking, so the
    #   row itself must survive regardless of top-5000 status — deleting it
    #   would wipe their OpenDota-tracked win_rate/form/mmr too. But this
    #   scraper IS the sole source of truth for whether they're STILL on
    #   Valve's official leaderboard (OpenDota's own leaderboard_rank field
    #   can lag behind Valve for a while after someone drops out — see the
    #   matching comment in dota2-community-site's sync-player-stats.mjs,
    #   which for this exact reason skips writing leaderboard_rank for any
    #   row this scraper manages). So once such a player disappears from the
    #   current fetch, clear leaderboard_rank/is_official_leaderboard here
    #   instead of deleting the row — that's the only place this ever gets
    #   reset back to null.
    stale_entries = request("GET", "?select=id,name,steam_id&is_official_leaderboard=eq.true") or []
    cleaned = 0
    for entry in stale_entries:
        if entry["name"] in fetched_names:
            continue

        if not entry.get("steam_id"):
            try:
                request("DELETE", f"?id=eq.{entry['id']}")
                cleaned += 1
            except RuntimeError as e:
                print(f"Failed to delete stale entry '{entry['name']}': {e}")
        else:
            try:
                request(
                    "PATCH",
                    f"?id=eq.{entry['id']}",
                    body={"leaderboard_rank": None, "is_official_leaderboard": False},
                    prefer="return=minimal",
                )
                cleaned += 1
            except RuntimeError as e:
                print(f"Failed to clear leaderboard status for '{entry['name']}': {e}")

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

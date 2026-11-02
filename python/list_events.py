"""Read recent stored events without modifying or creating the database."""

import argparse
import json
from pathlib import Path
import sqlite3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path(__file__).resolve().parents[1] / "data/traffic.db")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--assessment", choices=["suspected_red_light", "no_red_light_evidence", "unverified", "not_applicable_direction"])
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    if not args.database.is_file():
        parser.error("Database does not exist; run tracking first")
    try:
        connection = sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            where = " WHERE assessment=?" if args.assessment else ""
            parameters = [args.assessment, args.limit] if args.assessment else [args.limit]
            rows = connection.execute("SELECT payload_json FROM events" + where +
                                      " ORDER BY observed_at DESC, rowid DESC LIMIT ?", parameters).fetchall()
            print(f"Events: {len(rows)} | database: {args.database.resolve()}")
            for row in rows:
                event = json.loads(row[0])
                print(json.dumps(event, ensure_ascii=False, indent=2))
        finally:
            connection.close()
        return 0
    except (sqlite3.Error, ValueError) as exc:
        print(f"Cannot read events: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

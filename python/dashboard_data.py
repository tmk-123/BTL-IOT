"""Read-only, filtered SQLite queries for the local dashboard."""

from contextlib import closing
from pathlib import Path
import sqlite3


def load_events(database, assessment=None, vehicle_class=None, light_state=None,
                date_from=None, date_to=None, search="", limit=100, offset=0):
    path = Path(database).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Database does not exist: {path}")
    if not 1 <= limit <= 500 or offset < 0:
        raise ValueError("Require limit 1..500 and offset >= 0")
    clauses, values = [], []
    for key, value in (("assessment", assessment), ("vehicle_class", vehicle_class), ("light_state", light_state)):
        if value:
            clauses.append(f"{key}=?")
            values.append(value)
    if date_from:
        clauses.append("substr(observed_at,1,10)>=?")
        values.append(str(date_from))
    if date_to:
        clauses.append("substr(observed_at,1,10)<=?")
        values.append(str(date_to))
    if search:
        # Literal substring matching: '%' and '_' are not wildcards.
        clauses.append("(instr(event_id,?)>0 OR instr(source,?)>0 OR instr(CAST(track_id AS TEXT),?)>0)")
        values.extend([search] * 3)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN")
        total = connection.execute("SELECT count(*) FROM events" + where, values).fetchone()[0]
        summary = {row["assessment"]: row["n"] for row in connection.execute(
            "SELECT assessment,count(*) AS n FROM events" + where + " GROUP BY assessment", values)}
        rows = [dict(row) for row in connection.execute(
            "SELECT * FROM events" + where + " ORDER BY observed_at DESC,rowid DESC LIMIT ? OFFSET ?",
            values + [limit, offset])]
        return rows, total, summary

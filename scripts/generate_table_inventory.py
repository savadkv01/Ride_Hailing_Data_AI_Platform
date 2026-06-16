from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2 import sql

from env_loader import auto_load_env, postgres_connection_kwargs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate PostgreSQL table inventory with row counts.")
    parser.add_argument("--output-dir", default="logs/inventory", help="Directory for generated inventory files")
    parser.add_argument(
        "--include-views",
        action="store_true",
        help="Include views and materialized views in inventory",
    )
    return parser.parse_args()


def fetch_relations(conn, include_views: bool) -> list[tuple[str, str, str]]:
    table_types = ["BASE TABLE"]
    if include_views:
        table_types.extend(["VIEW", "MATERIALIZED VIEW"])

    query = """
        select table_schema, table_name, table_type
        from information_schema.tables
        where table_schema not in ('pg_catalog', 'information_schema')
          and table_type = any(%s)
        order by table_schema, table_name
    """

    with conn.cursor() as cur:
        cur.execute(query, (table_types,))
        return cur.fetchall()


def count_rows(conn, schema_name: str, relation_name: str) -> int | None:
    try:
        with conn.cursor() as cur:
            statement = sql.SQL("select count(*) from {}.{}").format(
                sql.Identifier(schema_name),
                sql.Identifier(relation_name),
            )
            cur.execute(statement)
            value = cur.fetchone()
            if not value:
                return None
            return int(value[0])
    except Exception:
        conn.rollback()
        return None


def relation_size(conn, schema_name: str, relation_name: str) -> int | None:
    try:
        with conn.cursor() as cur:
            cur.execute(
                "select pg_total_relation_size(%s::regclass)",
                (f"{schema_name}.{relation_name}",),
            )
            value = cur.fetchone()
            if not value:
                return None
            return int(value[0])
    except Exception:
        conn.rollback()
        return None


def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = ["schema", "relation", "type", "row_count", "size_bytes"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict], generated_at: str) -> None:
    total_relations = len(rows)
    total_rows = sum(int(r["row_count"]) for r in rows if isinstance(r["row_count"], int))
    lines = [
        "# PostgreSQL Table Inventory",
        "",
        f"Generated at: {generated_at}",
        f"Relations scanned: {total_relations}",
        f"Total rows (summed): {total_rows}",
        "",
        "| Schema | Relation | Type | Row Count | Size (bytes) |",
        "|---|---|---|---:|---:|",
    ]
    for row in rows:
        row_count = row["row_count"] if row["row_count"] is not None else "n/a"
        size_bytes = row["size_bytes"] if row["size_bytes"] is not None else "n/a"
        lines.append(
            f"| {row['schema']} | {row['relation']} | {row['type']} | {row_count} | {size_bytes} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    auto_load_env()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"postgres_table_inventory_{timestamp}.csv"
    md_path = output_dir / f"postgres_table_inventory_{timestamp}.md"

    conn = psycopg2.connect(**postgres_connection_kwargs())
    conn.autocommit = True

    relations = fetch_relations(conn, include_views=args.include_views)
    rows: list[dict] = []

    for schema_name, relation_name, relation_type in relations:
        row_count = count_rows(conn, schema_name, relation_name)
        size_bytes = relation_size(conn, schema_name, relation_name)
        rows.append(
            {
                "schema": schema_name,
                "relation": relation_name,
                "type": relation_type,
                "row_count": row_count,
                "size_bytes": size_bytes,
            }
        )

    conn.close()

    write_csv(csv_path, rows)
    write_markdown(md_path, rows, generated_at=datetime.now(timezone.utc).isoformat())

    print(f"inventory_csv={csv_path.as_posix()}")
    print(f"inventory_md={md_path.as_posix()}")
    print(f"relations_scanned={len(rows)}")


if __name__ == "__main__":
    main()

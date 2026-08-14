"""Load normalized CSV files into the MySQL schema in referential-integrity order."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


TABLE_FILES = [
    ("pais", "pais_final.csv"),
    ("uf", "uf_final.csv"),
    ("cidade", "cidade_final.csv"),
    ("orgao_superior", "orgao_superior_final.csv"),
    ("orgao_solicitante", "orgao_solicitante_final.csv"),
    ("servidor", "servidor_final.csv"),
    ("viagem", "viagem_final.csv"),
    ("trecho", "trecho_final.csv"),
]


def connect_db():
    load_dotenv()
    required = ["DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
    )


def read_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        for row in reader:
            yield reader.fieldnames, [None if value == "" else value for value in row.values()]


def load_table(cursor, conn, table: str, path: Path, batch_size: int) -> int:
    iterator = read_rows(path)
    try:
        columns, first_row = next(iterator)
    except StopIteration:
        return 0

    placeholders = ",".join(["%s"] * len(columns))
    column_sql = ",".join(f"`{column}`" for column in columns)
    sql = f"INSERT INTO `{table}` ({column_sql}) VALUES ({placeholders})"

    batch = [first_row]
    inserted = 0
    for _, row in iterator:
        batch.append(row)
        if len(batch) >= batch_size:
            cursor.executemany(sql, batch)
            conn.commit()
            inserted += len(batch)
            batch.clear()

    if batch:
        cursor.executemany(sql, batch)
        conn.commit()
        inserted += len(batch)

    return inserted


def truncate_tables(cursor, conn) -> None:
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table, _ in reversed(TABLE_FILES):
        cursor.execute(f"TRUNCATE TABLE `{table}`")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load normalized government-travel CSVs into MySQL.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--truncate", action="store_true", help="Clear target tables before loading.")
    args = parser.parse_args()

    conn = connect_db()
    cursor = conn.cursor()

    try:
        if args.truncate:
            truncate_tables(cursor, conn)

        for table, filename in TABLE_FILES:
            path = args.data_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"Missing processed file: {path}")
            count = load_table(cursor, conn, table, path, args.batch_size)
            print(f"Loaded {count:,} rows into {table}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()

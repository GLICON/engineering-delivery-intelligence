"""
load.py

Step 3: put the cleaned data into PostgreSQL and build the SQL views.

    python src/load.py            # load tables and build views
    python src/load.py --checks   # ...and print the data quality report

What it does, in order:
1. Runs sql/00_schema.sql to create empty tables.
2. Copies each CSV in data/processed/ into its table.
3. Runs every other .sql file in sql/ (in number order) to build the views.
"""

import sys

import pandas as pd
from sqlalchemy import create_engine

from config import PROCESSED_DIR, ROOT, database_url

SQL_FOLDER = ROOT / "sql"

# Load order matters: a pull request points at a release, so releases go first.
TABLES = ["releases", "pull_requests", "pr_issues", "reverts"]

# Columns that hold dates and must be read as dates, not text
DATE_COLUMNS = {
    "releases": ["released_at"],
    "pull_requests": ["created_at", "merged_at", "first_issue_created_at",
                      "first_release_at", "reverted_at"],
    "pr_issues": ["issue_created_at"],
    "reverts": ["reverted_at"],
}


def run_sql_file(engine, filename):
    """Run every statement in one .sql file."""
    sql = (SQL_FOLDER / filename).read_text()

    # Skip files that only contain comments (placeholders not written yet)
    code_lines = [line for line in sql.splitlines() if line.strip() and not line.strip().startswith("--")]
    if not code_lines:
        print(f"Skipping {filename} (no SQL in it yet)")
        return

    print(f"Running {filename}")
    connection = engine.raw_connection()   # a plain PostgreSQL connection
    try:
        connection.cursor().execute(sql)   # PostgreSQL runs every statement in the file
        connection.commit()                # save the changes
    finally:
        connection.close()


def load_csv_into_table(engine, table):
    """Read data/processed/<table>.csv and append it to delivery.<table>."""
    data = pd.read_csv(PROCESSED_DIR / f"{table}.csv", parse_dates=DATE_COLUMNS[table])
    data.to_sql(table, engine, schema="delivery", if_exists="append", index=False, chunksize=2000)
    print(f"Loaded {len(data):,} rows into delivery.{table}")


if __name__ == "__main__":
    engine = create_engine(database_url())

    run_sql_file(engine, "00_schema.sql")
    for table in TABLES:
        load_csv_into_table(engine, table)

    # 01_data_quality.sql, 02_delivery_metrics.sql, ... in number order
    for sql_file in sorted(SQL_FOLDER.glob("*.sql")):
        if sql_file.name != "00_schema.sql":
            run_sql_file(engine, sql_file.name)

    if "--checks" in sys.argv:
        report = pd.read_sql("SELECT * FROM delivery.data_quality_report", engine)
        print()
        print(report.to_string(index=False))
        if (report["status"] == "FAIL").any():
            sys.exit("A data quality check failed - see the report above.")

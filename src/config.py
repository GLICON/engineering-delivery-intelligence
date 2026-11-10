"""
config.py

Settings shared by every script: folder paths, the list of projects,
and how to connect to the database.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------
# ROOT is the top folder of the project (one level above src/).
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"              # downloaded data (not committed)
PROCESSED_DIR = ROOT / "data" / "processed"  # cleaned data (not committed)
REPORT_DIR = ROOT / "reports"                # charts and result tables

# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
# The GHPR dataset only stores a number for each project (repo_id).
# This table turns that number into the project's GitHub name.
# The GHPR README lists how many rows each project has, and every count is
# different, which is how each number was matched to its name.
REPOS = {
    46089560: "containerd/containerd",
    54230994: "coredns/coredns",
    65214191: "envoyproxy/envoy",
    1918677: "fluent/fluentd",
    50613991: "goharbor/harbor",
    43723161: "helm/helm",
    56342508: "jaegertracing/jaeger",
    20580498: "kubernetes/kubernetes",
    6838921: "prometheus/prometheus",
    62921553: "rook/rook",
    106598834: "theupdateframework/specification",
    48833910: "tikv/tikv",
    11008207: "vitessio/vitess",
}

# This one is a specification document, not software, so it has no releases.
# It is left out of the git history and the analysis.
SPEC_REPO = "theupdateframework/specification"

# GHPR stores who raised each issue as a number. These are GitHub's names.
AUTHOR_ROLES = {
    0: "COLLABORATOR",
    1: "CONTRIBUTOR",
    2: "FIRST_TIMER",
    3: "FIRST_TIME_CONTRIBUTOR",
    4: "MANNEQUIN",
    5: "MEMBER",
    6: "NONE",
    7: "OWNER",
}


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def database_url():
    """Build the PostgreSQL connection string from the .env file."""
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")  # reads DB_USER, DB_PASSWORD, ... into os.environ
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "engineering_delivery")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"

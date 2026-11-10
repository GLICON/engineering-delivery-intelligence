"""
acquire.py

Download the raw data into data/raw/.

    python src/acquire.py

This script downloads two things:

1. The GHPR dataset, which contains merged pull requests from
   13 open-source projects. I only keep the ghpr.csv file.

2. The Git history of those projects. I only need the commits
   and release tags, so --filter=tree:0 skips downloading the
   actual code files and saves space.

Both are downloaded using git clone, so no login is needed.

If the file or repository has already been downloaded, it is skipped.

Once finished, run:

    python src/git_history.py
"""

import shutil
import subprocess

from config import RAW_DIR, REPOS, SPEC_REPO

GHPR_URL = "https://github.com/soroushj/ghpr-dataset"


def download_ghpr():
    """Clone the GHPR repository and keep just its ghpr.csv file."""
    target = RAW_DIR / "ghpr.csv"
    if target.exists():
        print("ghpr.csv already downloaded")
        return

    temp_folder = RAW_DIR / "ghpr_temp"
    subprocess.run(["git", "clone", "--depth", "1", GHPR_URL, str(temp_folder)], check=True)
    shutil.copy(temp_folder / "ghpr.csv", target)
    shutil.rmtree(temp_folder)  # we only need the CSV
    print("Downloaded ghpr.csv")


def download_project_histories():
    """Clone each project's commit history (without the code files)."""
    git_folder = RAW_DIR / "git"
    git_folder.mkdir(exist_ok=True)

    for repo in REPOS.values():
        if repo == SPEC_REPO:
            continue  # no releases to read

        # e.g. "helm/helm" is saved as data/raw/git/helm_helm.git
        destination = git_folder / (repo.replace("/", "_") + ".git")
        if destination.exists():
            print(f"{repo}: already downloaded")
            continue

        print(f"{repo}: downloading history...")
        subprocess.run(
            ["git", "clone", "--quiet", "--bare", "--filter=tree:0",
             f"https://github.com/{repo}", str(destination)],
            check=True,
        )


if __name__ == "__main__":
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    download_ghpr()
    download_project_histories()
    print("Done. Next run: python src/git_history.py")

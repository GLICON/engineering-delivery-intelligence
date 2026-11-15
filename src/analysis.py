"""
analysis.py

Step 6: answer the business questions, print the results and save the charts.

    python src/analysis.py

Charts are saved to reports/figures/, and the regression results to
reports/cycle_time_model.csv.
"""

import matplotlib
matplotlib.use("Agg")  # draw charts to files without opening a window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sqlalchemy import create_engine

from config import REPORT_DIR, database_url
from feature_engineering import load_features

FIGURE_DIR = REPORT_DIR / "figures"
BLUE = "#2a78d6"     # one colour for all data
GREY = "#52514e"     # labels

# A clean chart style used by every chart below
plt.rcParams.update({
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e1e0d9", "axes.axisbelow": True,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "font.size": 10.5, "savefig.bbox": "tight", "figure.dpi": 110,
})

# Factors tested in the regression, with readable names for the chart
FACTORS = {
    "log2_lines_changed": "Lines changed (per doubling)",
    "log2_changed_files": "Files changed (per doubling)",
    "log2_commits": "Commits (per doubling)",
    "log2_review_comments": "Review comments (per doubling)",
    "fixes_several_issues": "Fixes more than one issue",
    "issue_from_outsider": "Issue raised by a non-maintainer",
    "opened_on_weekend": "PR opened at the weekend",
}


# ---------------------------------------------------------------------------
# Calculations
# ---------------------------------------------------------------------------
def cycle_time_model(df):
    """Which factors go with a slower merge, comparing PRs in the same project?

    This is a linear regression on log(time to merge). C(repo) adds a
    separate baseline for each project, so Kubernetes being big and slow
    does not distort the other results.
    """
    formula = "log_cycle_days ~ " + " + ".join(FACTORS) + " + C(repo)"
    model = smf.ols(formula, data=df).fit()

    # Because time is on a log scale, exp(coefficient) - 1 is the % change.
    # e.g. 0.42 -> exp(0.42) - 1 = +52% longer to merge.
    confidence = model.conf_int()
    results = pd.DataFrame({
        "factor": FACTORS.values(),
        "pct_change": [100 * (np.exp(model.params[f]) - 1) for f in FACTORS],
        "low": [100 * (np.exp(confidence.loc[f, 0]) - 1) for f in FACTORS],
        "high": [100 * (np.exp(confidence.loc[f, 1]) - 1) for f in FACTORS],
        "p_value": [model.pvalues[f] for f in FACTORS],
    })
    print(f"\nRegression: {int(model.nobs):,} PRs, R-squared = {model.rsquared:.2f}")
    return results.round(3)


def yearly_trend(df, repo=None):
    """Median days to merge and revert rate per year (optionally one project)."""
    if repo:
        df = df[df["repo"] == repo]
    df = df[df["merged_year"].between(2015, 2020)]
    return df.groupby("merged_year").agg(
        prs=("pull_number", "size"),
        median_cycle_days=("cycle_days", "median"),
        revert_rate_pct=("was_reverted", lambda x: 100 * x.mean()),
    ).round(2)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def save(fig, name):
    fig.savefig(FIGURE_DIR / name)
    plt.close(fig)


def chart_where_time_goes(df):
    """Bar chart: median days in review vs waiting to ship."""
    stages = pd.Series({
        "Waiting to ship": df["lead_time_days"].sub(df["cycle_days"]).median(),
        "Review and merge": df["cycle_days"].median(),
    })
    fig, ax = plt.subplots(figsize=(8, 2.6))
    bars = ax.barh(stages.index, stages.values, color=BLUE, height=0.5)
    ax.bar_label(bars, fmt="%.1f days", padding=6, color=GREY)
    ax.set_title("A merged fix waits far longer to ship than to be reviewed")
    ax.set_xlabel("Median days per pull request (all projects)")
    ax.set_xlim(0, stages.max() * 1.25)
    ax.grid(axis="y", visible=False)
    save(fig, "01_where_time_goes.png")


def chart_pr_size(size_table):
    """Two bar charts side by side: time to merge and revert rate by PR size."""
    # "1. XS (under 10 lines)" -> "XS\n(under 10 lines)": drop the number, wrap the range
    labels = [group.split(". ")[1].replace(" (", "\n(") for group in size_table.index]
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 3.8))

    bars = left.bar(labels, size_table["median_cycle_days"], color=BLUE, width=0.6)
    left.bar_label(bars, fmt="%.1f d", padding=3, color=GREY)
    left.set_title("Bigger PRs take longer to merge")
    left.set_ylabel("Median days, opened to merged")

    bars = right.bar(labels, size_table["revert_rate_pct"], color=BLUE, width=0.6)
    right.bar_label(bars, fmt="%.1f%%", padding=3, color=GREY)
    right.set_title("...and are reverted more often")
    right.set_ylabel("% of PRs later reverted")

    for ax in (left, right):
        ax.grid(axis="x", visible=False)
        ax.margins(y=0.15)
    save(fig, "02_pr_size.png")


def chart_speed_vs_reliability(yearly):
    """Two line charts: time to merge per year, and % of releases hotfixed."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 3.6))
    left.plot(yearly.index, yearly["median_cycle_days"], color=BLUE, linewidth=2, marker="o")
    left.set_title("Review got slower from 2015 to 2018...")
    left.set_ylabel("Median days to merge")

    right.plot(yearly.index, yearly["change_failure_rate_pct"], color=BLUE, linewidth=2, marker="o")
    right.set_title("...while releases needing a hotfix fell")
    right.set_ylabel("% of releases hotfixed within 7 days")

    for ax in (left, right):
        ax.set_ylim(bottom=0)
        ax.set_xticks(yearly.index)
    save(fig, "03_speed_vs_reliability.png")


def chart_model(results):
    """Dot-and-line chart of the regression results."""
    results = results.iloc[::-1]  # first factor at the top
    fig, ax = plt.subplots(figsize=(8, 3.8))
    y = range(len(results))
    ax.hlines(y, results["low"], results["high"], color=BLUE, linewidth=2)  # 95% range
    ax.plot(results["pct_change"], y, "o", color=BLUE, markersize=8)       # best estimate
    ax.axvline(0, color="#c3c2b7")                                         # "no effect" line
    ax.set_yticks(list(y), results["factor"])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("% change in time to merge (95% confidence range), same project")
    ax.set_title("Review discussion and extra commits matter more than size")
    save(fig, "04_cycle_time_drivers.png")


def chart_projects(dora):
    """Scatter: each project's lead time vs how often its releases needed a hotfix."""
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.scatter(dora["median_lead_time_days"], dora["change_failure_rate_pct"], s=60, color=BLUE)
    for _, row in dora.iterrows():
        ax.annotate(row["repo"].split("/")[1],
                    (row["median_lead_time_days"], row["change_failure_rate_pct"]),
                    xytext=(6, 4), textcoords="offset points", color=GREY, fontsize=9)
    ax.set_xlabel("Median lead time, PR opened to released (days)")
    ax.set_ylabel("Change failure rate (% releases hotfixed)")
    ax.set_title("Across projects, shipping speed and hotfix rate are only weakly linked")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=-1)  # a little space so a 0% project is not hidden on the axis
    save(fig, "05_projects_speed_vs_failure.png")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url())
    df = load_features()

    # Q1 Where is the bottleneck?
    print("\nMedian days in review:       ", round(df["cycle_days"].median(), 1))
    print("Median days waiting to ship: ", round(df["lead_time_days"].sub(df["cycle_days"]).median(), 1))
    chart_where_time_goes(df)

    # Q4 What goes with slow or failed changes?
    sizes = pd.read_sql("SELECT * FROM delivery.v_size_summary ORDER BY size_group", engine)
    print("\nBy PR size\n", sizes.to_string(index=False))
    chart_pr_size(sizes.set_index("size_group"))

    reviews = pd.read_sql("SELECT * FROM delivery.v_review_summary ORDER BY review_group", engine)
    print("\nBy review comments\n", reviews.to_string(index=False))

    results = cycle_time_model(df)
    print(results.to_string(index=False))
    results.to_csv(REPORT_DIR / "cycle_time_model.csv", index=False)
    chart_model(results)

    # Q3 Faster without becoming less reliable?
    yearly = pd.read_sql("SELECT * FROM delivery.v_speed_vs_reliability_yearly", engine).set_index("year")
    print("\nYear by year, all projects\n", yearly.to_string())
    # Same trend for Kubernetes alone, to check it is not just a change in project mix
    print("\nYear by year, Kubernetes only\n", yearly_trend(df, "kubernetes/kubernetes").to_string())
    chart_speed_vs_reliability(yearly)

    # Q2 / Q5 How fast is delivery, and how do projects differ?
    dora = pd.read_sql("SELECT * FROM delivery.v_dora_summary ORDER BY median_lead_time_days", engine)
    print("\nDORA summary per project\n", dora.to_string(index=False))
    dora.to_csv(REPORT_DIR / "dora_summary.csv", index=False)
    chart_projects(dora)

    print(f"\nCharts saved in {FIGURE_DIR}")

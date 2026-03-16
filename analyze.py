#!/usr/bin/env python3
"""Analyze SF 311 poop reports and generate a weekly trend chart."""

import math
import os
import re

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

DATA_CSV = os.path.join(os.path.dirname(__file__), "data", "sf_311_poop.csv")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
OUTPUT_PNG = os.path.join(OUTPUT_DIR, "weekly_poop_chart.png")

# Patterns for "not found" classification (DPW radio code 10-98)
NOT_FOUND_PATTERN = re.compile(
    r"10[/\-]?98|nothing found|nothing here|nothing foung|"
    r"No Work Needed|Not In Scope",
    re.IGNORECASE,
)

# Patterns for "cleaned" classification
CLEANED_PATTERN = re.compile(
    r"resolved|completed|done|steamed|clean|work completed", re.IGNORECASE
)

# Patterns for "other" (duplicates, transfers, etc.)
OTHER_PATTERN = re.compile(
    r"duplicate|transferred|insufficient|administrative closure", re.IGNORECASE
)


def classify(status_notes):
    """Classify a case by its status_notes."""
    if pd.isna(status_notes) or status_notes.strip() == "":
        return "other"
    s = str(status_notes)
    # Check not_found first since some "resolved" notes contain 10-98 codes
    if NOT_FOUND_PATTERN.search(s):
        return "not_found"
    if OTHER_PATTERN.search(s):
        return "other"
    if CLEANED_PATTERN.search(s):
        return "cleaned"
    return "other"


def main():
    # Load data
    df = pd.read_csv(DATA_CSV)
    print(f"Loaded {len(df)} rows.")

    # Parse dates
    df["requested_datetime"] = pd.to_datetime(df["requested_datetime"], utc=True)
    df["closed_date"] = pd.to_datetime(df["closed_date"], utc=True, errors="coerce")

    # Resolution time in days
    df["resolution_days"] = (
        df["closed_date"] - df["requested_datetime"]
    ).dt.total_seconds() / 86400

    # Classify
    df["category"] = df["status_notes"].apply(classify)

    # Week bucket (Monday start) — drop tz to avoid Period conversion warning
    df["week"] = df["requested_datetime"].dt.tz_localize(None).dt.to_period("W-SUN").dt.start_time

    # --- Weekly aggregations ---
    weekly_total = df.groupby("week").size().rename("total")

    # Median resolution (closed cases only, rounded to nearest 0.5 day)
    closed = df[df["resolution_days"].notna() & (df["resolution_days"] >= 0)]
    weekly_median_res = closed.groupby("week")["resolution_days"].median().rename(
        "median_resolution_days"
    )
    weekly_median_res = weekly_median_res.apply(lambda x: round(x * 2) / 2)

    # % cleaned: cleaned / (total - duplicates)
    def cleaned_ratio(group):
        non_dup = group[group["category"] != "other"]
        # Keep not_found in denominator, only exclude "other"
        # Actually per plan: exclude duplicates from denominator but keep transfers etc.
        # Let's be more precise: exclude only duplicates
        is_dup = group["status_notes"].str.contains(
            "duplicate", case=False, na=False
        )
        denom = len(group) - is_dup.sum()
        if denom == 0:
            return float("nan")
        cleaned_count = (group["category"] == "cleaned").sum()
        return cleaned_count / denom

    weekly_cleaned = df.groupby("week").apply(cleaned_ratio).rename("cleaned_ratio")

    weekly = pd.concat([weekly_total, weekly_median_res, weekly_cleaned], axis=1)
    weekly = weekly.sort_index()

    # Drop partial first/last weeks if they have very few reports
    if len(weekly) > 2:
        weekly = weekly.iloc[1:-1]

    # --- Plot: three separate subplots ---
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), sharex=True)

    color_reports = "#2196F3"
    color_resolution = "#FF9800"
    color_cleaned = "#4CAF50"

    # Chart 1: reports per week
    ax1.plot(
        weekly.index, weekly["total"], color=color_reports, linewidth=1, alpha=0.8,
    )
    ax1.set_ylabel("Reports per week")
    ax1.set_title("SF 311 Human or Animal Waste Reports — Weekly Trends")

    # Chart 2: median resolution days
    ax2.plot(
        weekly.index, weekly["median_resolution_days"],
        color=color_resolution, linewidth=1, alpha=0.8,
    )
    ax2.set_ylabel("Median resolution (days)")
    ax2.yaxis.set_major_locator(plt.MultipleLocator(10))
    ax2.yaxis.set_minor_locator(plt.MultipleLocator(2))
    # Alternating color bands every 2 days
    y_max = weekly["median_resolution_days"].max()
    for y in range(0, int(y_max) + 4, 2):
        color = "#FF9800" if (y // 2) % 2 == 0 else "#FFE0B2"
        ax2.axhspan(y, y + 2, color=color, alpha=0.15)

    # Chart 3: cleaned ratio
    ax3.plot(
        weekly.index, weekly["cleaned_ratio"],
        color=color_cleaned, linewidth=1, alpha=0.8,
    )
    ax3.set_ylabel("% cleaned")
    ax3.set_ylim(0, 1.05)
    ax3.set_xlabel("Week")

    for ax in (ax1, ax2, ax3):
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    fig.tight_layout()
    fig.savefig(OUTPUT_PNG, dpi=150)
    print(f"Chart saved to {OUTPUT_PNG}")


if __name__ == "__main__":
    main()

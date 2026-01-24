from flask import Flask, render_template
import os
import pandas as pd
from dotenv import load_dotenv
import math

app = Flask(__name__)

# Load .env if present (safe for both local and EC2)
load_dotenv()

def load_dataset():
    source = os.getenv("DATA_SOURCE", "local").lower()

    if source == "local":
        path = os.getenv(
            "LOCAL_DATA_PATH",
            "data/GraduateEmployment.csv"
        )

        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Local dataset not found at {path}"
            )

        return pd.read_csv(path)

    if source == "s3_presigned":
        url = os.getenv("S3_PRESIGNED_URL")

        if not url:
            raise RuntimeError(
                "S3_PRESIGNED_URL is not set"
            )

        try:
            return pd.read_csv(url)
        except Exception as e:
            raise RuntimeError(
                "Failed to load dataset from pre-signed URL. "
                "It may have expired."
            ) from e

    raise RuntimeError(
        f"Unknown DATA_SOURCE value: {source}"
    )

def compute_employability_stability(df: pd.DataFrame, group_col: str = "university"):
    """
    Computes stability index per group based on yearly average employment_rate_overall:
      stability_index = mean(employment_rate_overall_by_year) / std(...)
    Returns: (stats_df, series_df, years)
      - stats_df columns: group, mean, std, stability_index
      - series_df columns: group, year, employment_rate_overall (yearly avg)
      - years: sorted list of years in dataset
    """
    required = {"year", group_col, "employment_rate_overall"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")

    work = df.copy()
    work["employment_rate_overall"] = pd.to_numeric(work["employment_rate_overall"], errors="coerce")
    work = work.dropna(subset=["employment_rate_overall", "year", group_col])

    # Yearly average per group (prevents groups with more degrees from overweighting a year)
    series_df = (
        work.groupby([group_col, "year"], as_index=False)["employment_rate_overall"]
        .mean()
        .rename(columns={group_col: "group"})
    )

    stats_df = (
        series_df.groupby("group")["employment_rate_overall"]
        .agg(mean="mean", std="std")
        .reset_index()
    )

    # Guard against std=0 (would blow up to inf). If std==0, set index to None.
    def safe_index(row):
        if row["std"] is None or (isinstance(row["std"], float) and (math.isnan(row["std"]) or row["std"] == 0.0)):
            return None
        return row["mean"] / row["std"]

    stats_df["stability_index"] = stats_df.apply(safe_index, axis=1)

    years = sorted(series_df["year"].unique().tolist())
    return stats_df, series_df, years

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/function1")
def function1():
    df = load_dataset()

    # Change group_col to "degree" if you want the index by degree instead.
    stats_df, series_df, years = compute_employability_stability(df, group_col="university")

    # --- Chart 1: Ranked bar chart (Stability Index) ---
    ranked = stats_df.dropna(subset=["stability_index"]).sort_values("stability_index", ascending=False)
    bar_labels = ranked["group"].tolist()
    bar_values = [round(v, 3) for v in ranked["stability_index"].tolist()]

    # --- Chart 2: Scatter plot (Mean vs Std Dev) ---
    scatter_points = []
    for _, r in stats_df.iterrows():
        if pd.isna(r["mean"]) or pd.isna(r["std"]):
            continue
        scatter_points.append({
            "label": r["group"],
            "x": round(float(r["mean"]), 3),   # Mean on X
            "y": round(float(r["std"]), 3),    # Std Dev on Y
        })

    # --- Chart 3: Line chart (top 3 + bottom 3 by Stability Index) ---
    top3 = ranked.head(3)["group"].tolist()
    bottom3 = ranked.tail(3)["group"].tolist()
    selected = top3 + [g for g in bottom3 if g not in top3]

    # Build year -> value per group (fill gaps with None so Chart.js breaks the line)
    pivot = series_df.pivot_table(index="year", columns="group", values="employment_rate_overall", aggfunc="mean")
    line_datasets = []
    for g in selected:
        vals = []
        for y in years:
            v = pivot.loc[y, g] if (y in pivot.index and g in pivot.columns) else None
            vals.append(None if pd.isna(v) else round(float(v), 2))
        line_datasets.append({
            "label": g,
            "data": vals
        })

    return render_template(
        "function1.html",
        bar_labels=bar_labels,
        bar_values=bar_values,
        scatter_points=scatter_points,
        years=years,
        line_datasets=line_datasets,
        top3=top3,
        bottom3=bottom3
    )

@app.route("/function2")
def function2():
    return render_template("function2.html")

@app.route("/function3")
def function3():
    return render_template("function3.html")

@app.route("/function4")
def function4():
    return render_template("function4.html")

@app.route("/function5")
def function5():
    return render_template("function5.html")

@app.route("/api/preview")
def preview():
    df = load_dataset()
    return df.head(10).to_json(orient="records")

if __name__ == "__main__":
    app.run(debug=True)

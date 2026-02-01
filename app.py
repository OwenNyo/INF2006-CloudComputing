from flask import Flask, render_template, jsonify, request
import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import math

app = Flask(__name__)

# Load .env if present (safe for both local and EC2)
load_dotenv()


def load_dataset():
    source = os.getenv("DATA_SOURCE", "local").lower()

    if source == "s3_presigned":
        url = os.getenv("S3_PRESIGNED_URL")

        if not url:
            raise RuntimeError("S3_PRESIGNED_URL is not set")

        try:
            return pd.read_csv(url)
        except Exception as e:
            raise RuntimeError(
                "Failed to load dataset from pre-signed URL. " "It may have expired."
            ) from e
    else:
        path = os.getenv("LOCAL_DATA_PATH")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Local dataset not found at {path}")

        return pd.read_csv(path)

    raise RuntimeError(f"Unknown DATA_SOURCE value: {source}")


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


def compute_salary_trend_analysis(df: pd.DataFrame, universities=None, start_year=None, end_year=None):
    """
    Computes salary trend analysis with moving averages and linear trend lines.
    Allows filtering by universities and time period.
    """
    work = df.copy()
    
    work["gross_monthly_median"] = pd.to_numeric(work["gross_monthly_median"], errors="coerce")
    work["year"] = pd.to_numeric(work["year"], errors="coerce")
    
    # Remove rows with missing required fields
    work = work.dropna(subset=["year", "university", "gross_monthly_median"])
    
    # Convert year to int for proper filtering
    work["year"] = work["year"].astype(int)
    
    # Filter by time period if specified
    if start_year is not None:
        work = work[work["year"] >= start_year]
    if end_year is not None:
        work = work[work["year"] <= end_year]
    
    # Filter by universities if specified
    if universities:
        work = work[work["university"].isin(universities)]
    
    # Get yearly median salary by university (averaging across degrees)
    yearly_salary = (
        work.groupby(["university", "year"], as_index=False)["gross_monthly_median"]
        .mean()
        .round(2)
    )
    
    years = sorted(yearly_salary["year"].unique())
    available_universities = sorted(yearly_salary["university"].unique())
    
    # Calculate trend data for each university
    university_data = {}
    
    for university in available_universities:
        univ_data = yearly_salary[yearly_salary["university"] == university].sort_values("year")
        
        if len(univ_data) < 2:
            continue
            
        salaries = univ_data["gross_monthly_median"].tolist()
        univ_years = univ_data["year"].tolist()
        
        # 3-year moving average
        moving_avg = []
        for i in range(len(salaries)):
            if i >= 2:
                avg_3yr = np.mean(salaries[i-2:i+1])
                moving_avg.append(round(avg_3yr, 2))
            elif i == 1:
                avg_2yr = np.mean(salaries[i-1:i+1])
                moving_avg.append(round(avg_2yr, 2))
            else:
                moving_avg.append(salaries[i])
        
        # Linear trend line
        if len(salaries) >= 2:
            trend_slope, trend_intercept = np.polyfit(univ_years, salaries, 1)
            trend_line = [trend_slope * year + trend_intercept for year in univ_years]
            trend_line = [round(val, 2) for val in trend_line]
        else:
            trend_line = salaries
            trend_slope = 0
        
        university_data[university] = {
            "years": [int(year) for year in univ_years],  
            "salaries": [float(salary) for salary in salaries],  
            "moving_averages": [float(avg) for avg in moving_avg],  
            "trend_line": [float(val) for val in trend_line],  
            "trend_slope": float(trend_slope),  
            "data_points": int(len(salaries)),  
            "salary_change": float(salaries[-1] - salaries[0]) if len(salaries) >= 2 else 0.0,
            "salary_change_pct": float((salaries[-1] - salaries[0]) / salaries[0] * 100) if len(salaries) >= 2 and salaries[0] > 0 else 0.0
        }
    
    return {
        "universities": university_data,
        "all_universities": available_universities,
        "years_range": [int(year) for year in years],  
        "filtered_period": {
            "start_year": int(min(years)) if years else None,
            "end_year": int(max(years)) if years else None
        }
    }


def compute_university_roi(df: pd.DataFrame, year=None, start_year=None, end_year=None):
    filtered = df.copy()

    # Ensure numeric types (GES often stores as text)
    filtered["employment_rate_ft_perm"] = pd.to_numeric(
        filtered["employment_rate_ft_perm"], errors="coerce"
    )
    filtered["gross_monthly_median"] = pd.to_numeric(
        filtered["gross_monthly_median"], errors="coerce"
    )
    filtered["year"] = pd.to_numeric(filtered["year"], errors="coerce")

    # Drop rows missing required values
    filtered = filtered.dropna(
        subset=["year", "university", "employment_rate_ft_perm", "gross_monthly_median"]
    )

    # Optional filters
    if year is not None:
        filtered = filtered[filtered["year"] == year]

    if start_year is not None and end_year is not None:
        filtered = filtered[
            (filtered["year"] >= start_year) & (filtered["year"] <= end_year)
        ]

    grouped = (
        filtered.groupby("university")
        .agg(
            avg_ft_employment_rate=("employment_rate_ft_perm", "mean"),
            avg_median_salary=("gross_monthly_median", "mean"),
        )
        .reset_index()
    )

    grouped["roi_score"] = (
        grouped["avg_ft_employment_rate"] * grouped["avg_median_salary"]
    )
    grouped = grouped.sort_values(by="roi_score", ascending=False).round(2)

    return grouped


@app.route("/api/roi/university", methods=["GET"])
def university_roi():
    year = request.args.get("year", type=int)
    start_year = request.args.get("start_year", type=int)
    end_year = request.args.get("end_year", type=int)

    df = load_dataset()

    result_df = compute_university_roi(
        df=df, year=year, start_year=start_year, end_year=end_year
    )

    return jsonify(
        {
            "metric": "University ROI Proxy",
            "definition": "FT Employment Rate × Gross Monthly Median Salary",
            "filters": {"year": year, "start_year": start_year, "end_year": end_year},
            "results": result_df.to_dict(orient="records"),
        }
    )


@app.route("/")
def home():
    return render_template(
        "index.html",
        brand_sub="Home Page",
    )


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
        brand_sub="Employment Stability Index",
        active_page="function1",
        bar_labels=bar_labels,
        bar_values=bar_values,
        scatter_points=scatter_points,
        years=years,
        line_datasets=line_datasets,
        top3=top3,
        bottom3=bottom3,
    )



#------------ Function 2 ------------#
@app.route("/function2")
def function2():
    return render_template(
        "function2.html",
        brand_sub="Salary vs Employment Trade-off",
        active_page="function2",
    )


@app.route("/function2graph")
def function2graph():
    group_by = request.args.get("group_by", "degree")
    df = load_dataset()
    df["gross_monthly_median"] = pd.to_numeric(df["gross_monthly_median"], errors="coerce")
    df["employment_rate_ft_perm"] = pd.to_numeric(df["employment_rate_ft_perm"], errors="coerce")

    # Drop rows with missing numeric values
    df = df.dropna(subset=[group_by, "employment_rate_ft_perm", "gross_monthly_median"])

    grouped = (
        df.groupby(group_by)
        .agg(
            avg_salary=("gross_monthly_median", "mean"),
            avg_employment=("employment_rate_ft_perm", "mean")
        )
        .reset_index()
    )
    labels = grouped[group_by].tolist()
    salaries = grouped["avg_salary"].tolist()
    employment = grouped["avg_employment"].tolist()

    return jsonify({
        "labels": labels,
        "salary": salaries,
        "employment": employment
    })

#------------------------------------#

@app.route("/function3")
def function3():

    df = load_dataset()

    # years in dataset only (sorted)
    years = (
        pd.to_numeric(df["year"], errors="coerce")
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )
    years = sorted(years)

    # Compute initial ROI for full range (so page loads with data immediately)
    initial_df = compute_university_roi(
        df=df,
        start_year=years[0] if years else None,
        end_year=years[-1] if years else None,
    )

    initial_results = initial_df.to_dict(orient="records")

    # Optional: Top3/Bottom3 by ROI score (nice for hero summary)
    top3 = [r["university"] for r in initial_results[:3]]
    bottom3 = [r["university"] for r in initial_results[-3:]]

    return render_template(
        "function3.html",
        brand_sub="University ROI Proxy",
        active_page="function3",
        years=years,
        initial_results=initial_results,
        top3=top3,
        bottom3=bottom3,
    )


@app.route("/function4")
def function4():
    df = load_dataset()
    
    # Get all available universities for dropdown
    all_universities = sorted(df["university"].dropna().unique().tolist())
    
    # Get all available years for period selection
    all_years = sorted(pd.to_numeric(df["year"], errors="coerce").dropna().astype(int).unique().tolist())
    
    # Default selection: top 5 universities by latest salary
    latest_year = max(all_years)
    
    # Convert gross_monthly_median to numeric for mean calculation
    df_latest = df[df["year"] == latest_year].copy()
    df_latest["gross_monthly_median"] = pd.to_numeric(df_latest["gross_monthly_median"], errors="coerce")
    
    latest_salaries = df_latest.groupby("university")["gross_monthly_median"].mean().sort_values(ascending=False)
    default_universities = latest_salaries.head(5).index.tolist()
    
    return render_template(
        "function4.html",
        brand_sub="Salary Trend Analysis",
        active_page="function4",
        
        # Selection options
        all_universities=all_universities,
        all_years=all_years,
        default_universities=default_universities
    )


@app.route("/function5")
def function5():
    return render_template(
        "function5.html",
        brand_sub="Function 5 Dashboard",
        active_page="function5",
    )


@app.route("/api/salary-trends", methods=["POST"])
def salary_trends_api():
    """API endpoint for dynamic salary trend analysis"""
    data = request.get_json()
    
    universities = data.get("universities", [])
    start_year = data.get("start_year")
    end_year = data.get("end_year")
    
    df = load_dataset()
    trend_data = compute_salary_trend_analysis(
        df=df,
        universities=universities if universities else None,
        start_year=start_year,
        end_year=end_year
    )
    
    # Prepare chart datasets
    chart_datasets = []
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#4BC0C0', '#FF6384', '#36A2EB']
    
    for i, (university, data) in enumerate(trend_data["universities"].items()):
        color = colors[i % len(colors)]
        
        # Raw salary data
        chart_datasets.append({
            "label": f"{university} - Actual",
            "data": [float(x) for x in data["salaries"]],  # Ensure Python float
            "borderColor": color,
            "backgroundColor": color + "20",
            "fill": False,
            "borderWidth": 2,
            "pointRadius": 4,
            "type": "line"
        })
        
        # Moving average
        chart_datasets.append({
            "label": f"{university} - 3yr MA",
            "data": [float(x) for x in data["moving_averages"]],  # Ensure Python float
            "borderColor": color,
            "backgroundColor": color + "10",
            "borderDash": [5, 5],
            "fill": False,
            "borderWidth": 2,
            "pointRadius": 2,
            "type": "line"
        })
        
        # Trend line
        chart_datasets.append({
            "label": f"{university} - Trend",
            "data": [float(x) for x in data["trend_line"]],  # Ensure Python float
            "borderColor": color,
            "backgroundColor": color + "05",
            "borderDash": [10, 5],
            "fill": False,
            "borderWidth": 1,
            "pointRadius": 0,
            "type": "line"
        })
    
    return jsonify({
        "chart_datasets": chart_datasets,
        "years_range": trend_data["years_range"],
        "university_data": trend_data["universities"],
        "filtered_period": trend_data["filtered_period"]
    })


@app.route("/api/preview")
def preview():
    df = load_dataset()
    return df.head(10).to_json(orient="records")


if __name__ == "__main__":
    app.run(debug=True)

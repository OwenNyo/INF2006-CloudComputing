from flask import Flask, render_template, request, jsonify
import os
import pandas as pd
from dotenv import load_dotenv

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

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/function1")
def function1():
    return render_template("function1.html")


#------------ Function 2 ------------#
@app.route("/function2")
def function2():
    return render_template("function2.html")

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

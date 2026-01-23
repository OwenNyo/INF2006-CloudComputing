from flask import Flask, render_template
import os
import pandas as pd
from dotenv import load_dotenv
from functools import lru_cache

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

@lru_cache(maxsize=1)
def get_dataset():
    return load_dataset()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/function1")
def function1():
    return render_template("function1.html")

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
    df = get_dataset()
    return df.head(10).to_json(orient="records")

if __name__ == "__main__":
    app.run(debug=True)

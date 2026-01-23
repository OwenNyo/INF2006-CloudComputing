from flask import Flask, render_template

app = Flask(__name__)

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

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h1>VirtuCAN Automotive CAN Diagnostics</h1>
    <p>Web dashboard is running successfully!</p>
    """

if __name__ == "__main__":
    app.run()

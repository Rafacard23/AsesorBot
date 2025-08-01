from flask import Flask
import os

app = Flask(__name__)

@app.route("/")
def health():
    return {"status": "Bot is alive"}, 200

def run_flask(port=None):
    """Start Flask on dynamic port."""
    port = int(os.getenv("PORT", port or 5000))
    app.run(host="0.0.0.0", port=port)

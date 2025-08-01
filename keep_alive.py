from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route("/")
def ok():
    return jsonify({"status": "Bot is alive"}), 200

# No hace falta más; gunicorn arranca esto directamente

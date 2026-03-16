"""
app.py — Flask application entry point.
Run:  python app.py
Then open http://localhost:5000 in your browser.
"""
import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from routes import api

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR  = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
CORS(app)                              # allow fetch() from any origin (dev friendly)

# Register API blueprint
app.register_blueprint(api, url_prefix="/api")

# Serve frontend
@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  🌐  LogistiPath  —  Global Logistics Pathfinding")
    print("  🚀  Server running at  http://localhost:5000")
    print("=" * 60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

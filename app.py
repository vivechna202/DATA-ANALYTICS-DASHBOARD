import logging

from flask import Flask, render_template

from analytics_dashboard.routes.query_routes import query_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = Flask(
    __name__,
    template_folder="analytics_dashboard/templates"
)

app.register_blueprint(query_bp)

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
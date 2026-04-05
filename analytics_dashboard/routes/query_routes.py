from flask import Blueprint, jsonify, request

from analytics_dashboard.services.query_service import process_query

query_bp = Blueprint("query", __name__)


@query_bp.route("/query", methods=["POST"])
def query():
    data = request.get_json(silent=True) or {}
    user_query = data.get("query", "")
    source_type = data.get("source_type", "auto")
    source_input = data.get("source_input")
    mongo_database = data.get("mongo_database")
    mongo_collection = data.get("mongo_collection")
    mongo_limit = data.get("mongo_limit")

    result = process_query(
        user_query,
        source_type=source_type,
        source_input=source_input,
        mongo_database=mongo_database,
        mongo_collection=mongo_collection,
        mongo_limit=mongo_limit,
    )

    if result.get("error"):
        return jsonify(result), 400

    return jsonify(result)

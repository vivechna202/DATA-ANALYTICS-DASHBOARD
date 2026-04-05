from flask import Blueprint, request, jsonify
from analytics_dashboard.services.query_service import handle_query
from analytics_dashboard.rag.pipeline import RAGPipeline

query_bp = Blueprint("query", __name__)

# Initialize RAG once
rag_pipeline = RAGPipeline("analytics_dashboard/data/documents/pdf-data.pdf")


@query_bp.route("/query", methods=["POST"])
def query():
    try:
        data = request.get_json()
        user_query = data.get("query", "").lower()

        # Step 1: Try CSV logic first
        result = handle_query(user_query)

        # Step 2: If not understood → use RAG
        if result.get("message") == "Query not understood":
            rag_result = rag_pipeline.query(user_query)

            return jsonify({
                "answer": rag_result["answer"],
                "source": "rag"
            })

        # Step 3: Return CSV result
        result["source"] = "csv"
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
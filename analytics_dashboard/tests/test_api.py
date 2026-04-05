"""Manual smoke script — run from project root: python -m analytics_dashboard.tests.test_api"""

from analytics_dashboard.rag.pipeline import RAGPipeline

if __name__ == "__main__":
    pipeline = RAGPipeline("analytics_dashboard/data/documents/pdf-data.pdf")
    q = "Which products have high stock?"
    response = pipeline.query(q)
    print("\nFinal answer:\n")
    print(response["answer"])

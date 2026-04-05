from rag.pipeline import RAGPipeline

pipeline = RAGPipeline("data/documents/pdf-data.pdf")

query = "Which products have high stock?"

response = pipeline.query(query)

print("\n🧠 Final Answer:\n")
print(response["answer"])
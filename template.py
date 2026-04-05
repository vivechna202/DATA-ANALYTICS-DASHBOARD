import os
from pathlib import Path

project_name = "analytics_dashboard"

list_of_files = [

    # 🔹 Core App
    "app.py",
    "config.py",
    "requirements.txt",
    "README.md",

    # 🔹 Data Layer
    f"{project_name}/data/__init__.py",
    f"{project_name}/data/sales.csv",
    f"{project_name}/data/processed_data.csv",
    f"{project_name}/data/documents/sample.pdf",

    # 🔹 Models (LLM + Embeddings)
    f"{project_name}/models/__init__.py",
    f"{project_name}/models/embedding_model.py",
    f"{project_name}/models/llm_model.py",
    f"{project_name}/models/intent_classifier.py",

    # 🔹 RAG Pipeline
    f"{project_name}/rag/__init__.py",
    f"{project_name}/rag/chunking.py",
    f"{project_name}/rag/embeddings.py",
    f"{project_name}/rag/vector_store.py",
    f"{project_name}/rag/retriever.py",
    f"{project_name}/rag/pipeline.py",

    # 🔹 Routes (API Layer)
    f"{project_name}/routes/__init__.py",
    f"{project_name}/routes/query_routes.py",
    f"{project_name}/routes/data_routes.py",
    f"{project_name}/routes/visualization_routes.py",

    # 🔹 Services (Business Logic)
    f"{project_name}/services/__init__.py",
    f"{project_name}/services/query_service.py",
    f"{project_name}/services/data_service.py",
    f"{project_name}/services/visualization_service.py",
    f"{project_name}/services/rag_service.py",

    # 🔹 Utils
    f"{project_name}/utils/__init__.py",
    f"{project_name}/utils/helpers.py",
    f"{project_name}/utils/logger.py",
    f"{project_name}/utils/text_cleaner.py",

    # 🔹 Frontend
    f"{project_name}/static/css/styles.css",
    f"{project_name}/static/js/main.js",
    f"{project_name}/static/js/api.js",
    f"{project_name}/static/js/charts.js",
    f"{project_name}/static/images/.gitkeep",

    f"{project_name}/templates/index.html",
    f"{project_name}/templates/dashboard.html",

    # 🔹 Notebooks (optional)
    f"{project_name}/notebooks/analysis.ipynb",

    # 🔹 Tests
    f"{project_name}/tests/__init__.py",
    f"{project_name}/tests/test_api.py",
    f"{project_name}/tests/test_rag.py",

    # 🔹 Deployment (optional)
    "Dockerfile",
    ".dockerignore",
]

# 🔧 Create files
for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)

    if filedir != "":
        os.makedirs(filedir, exist_ok=True)

    if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
        with open(filepath, "w") as f:
            pass
    else:
        print(f"File already exists at: {filepath}")

print("✅ Project structure created successfully!")
*PROJECT INITIALIZATION
    analytics_dashboard/
    │
    ├── routes/        → handles API requests
    ├── services/      → business logic
    ├── data/          → dataset

*ENVIRONMENT SETUP

*PACKAGE SETUP(setup.py)

*BACKEND PROCESS
    1. User types → "sales trend"
    2. JS sends POST request → Flask API
    3. Flask → query_routes → query_service
    4. Pandas processes data
    5. Plotly generates chart
    6. JSON returned
    7. JS renders chart using Plotly

// beacuse of csv file we added we are able to get anwers for the querries 
//Right now:
   User → CSV → Answer
  After RAG:
   User → Embedding → Vector DB → Relevant Docs → LLM → Answer
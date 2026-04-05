import pandas as pd
import plotly.express as px

df = pd.read_csv("analytics_dashboard/data/sales.csv")


def handle_query(query):
    query = query.lower()

    if "total sales" in query:
        total = df['sales'].sum()
        return {"answer": f"Total sales is {total}"}

    elif "average sales" in query:
        avg = df['sales'].mean()
        return {"answer": f"Average sales is {avg:.2f}"}

    elif "trend" in query:
        fig = px.line(df, x="date", y="sales", title="Sales Trend")

        return {
            "answer": "Here is the sales trend",
            "chart": fig.to_json()
        }

    else:
        return {"message": "Query not understood"}
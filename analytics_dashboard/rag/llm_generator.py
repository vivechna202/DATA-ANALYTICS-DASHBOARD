import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("❌ GOOGLE_API_KEY not found in .env file")

client = genai.Client(api_key=api_key)


def get_available_flash_model():
    """
    Finds a working Gemini Flash model dynamically.
    """
    try:
        print("🔍 Fetching available models...")
        models = client.models.list()

        available_models = []
        for m in models:
            print(f"➡️ Found model: {m.name}")
            available_models.append(m.name)

        # Priority: gemini-2.0-flash
        for name in available_models:
            if "gemini-2.0-flash" in name:
                print(f"✅ Using model: {name}")
                return name

        # Fallback: any flash model
        for name in available_models:
            if "flash" in name:
                print(f"✅ Using fallback flash model: {name}")
                return name

        fallback = "gemini-2.0-flash"
        print(f"⚠️ No flash model found, using fallback: {fallback}")
        return fallback

    except Exception as e:
        print("❌ Error fetching models:", str(e))
        return "gemini-2.0-flash"


# Initialize model
SELECTED_MODEL = get_available_flash_model()


def generate_answer(query, context_chunks):
    """
    Generates answer using Gemini model.
    Falls back to rule-based + RAG chunks if API fails.
    """
    context = "\n\n".join(context_chunks)

    prompt = f"""
You are a smart data analyst. Use ONLY the context below.

Context:
{context}

Question:
{query}

Answer:
"""

    try:
        print(f"\n🔍 Using model: {SELECTED_MODEL}")
        print(f"📝 Query: {query}")

        response = client.models.generate_content(
            model=SELECTED_MODEL,
            contents=prompt
        )

        if response and hasattr(response, "text") and response.text:
            return response.text.strip()
        else:
            raise ValueError("Empty response from model")

    except Exception as e:
        print("❌ LLM Error:", str(e))

        # 🔥 FALLBACK MODE
        fallback_answer = build_fallback_answer(query, context_chunks)

        return f"""
⚠️ LLM unavailable (fallback mode)

📌 Answer (from document):
{fallback_answer}
"""


def build_fallback_answer(query, chunks):
    """
    Intelligent fallback without LLM
    """
    query = query.lower()

    # 🔹 Case: Highest stock
    if "highest stock" in query or "high stock" in query:
        max_stock = -1
        best_line = ""

        for chunk in chunks:
            lines = chunk.split("\n")
            for line in lines:
                parts = line.split()

                if len(parts) >= 6:
                    try:
                        stock = int(parts[-1])  # last column = stock
                        if stock > max_stock:
                            max_stock = stock
                            best_line = line
                    except:
                        continue

        if best_line:
            return f"Product with highest stock:\n{best_line}"

    # 🔹 Default fallback
    return "\n\n".join(chunks[:2])
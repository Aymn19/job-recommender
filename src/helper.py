import os
import fitz  # PyMuPDF
import ollama


def extract_text_from_pdf(uploaded_file):
    """
    Extract text from an uploaded PDF file.
    """

    try:
        uploaded_file.seek(0)

        doc = fitz.open(
            stream=uploaded_file.read(),
            filetype="pdf"
        )

        text = "\n".join(
            page.get_text() for page in doc
        )

        doc.close()

        if not text.strip():
            return "Aucun texte détecté dans ce PDF."

        return text.strip()

    except Exception as e:
        raise ValueError(
            f"Impossible de lire le PDF : {e}"
        ) from e


def ask_openai(prompt, max_tokens=500):
    """
    Generate an AI response using Ollama Cloud.
    The function name is preserved for compatibility with app.py.
    """

    api_key = os.getenv("OLLAMA_API_KEY")

    if not api_key:
        return (
            "Configuration Error: OLLAMA_API_KEY is missing. "
            "Configure this variable in Streamlit Cloud Secrets."
        )

    try:
        client = ollama.Client(
            host="https://ollama.com",
            headers={
                "Authorization": f"Bearer {api_key}"
            }
        )

        response = client.chat(
            model="gpt-oss:20b-cloud",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "temperature": 0.5,
                "num_predict": max_tokens
            }
        )

        return response["message"]["content"]

    except Exception as e:
        return f"Ollama Cloud Error: {str(e)}"

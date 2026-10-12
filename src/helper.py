
import os
import fitz
import ollama


def extract_text_from_pdf(uploaded_file):
    """Extract text from an uploaded PDF."""

    if uploaded_file is None:
        raise ValueError("Aucun fichier PDF fourni.")

    try:
        uploaded_file.seek(0)
        pdf_bytes = uploaded_file.read()

        if not pdf_bytes:
            raise ValueError("Le fichier PDF est vide.")

        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            text = "\n".join(page.get_text("text") for page in doc)

        if not text.strip():
            raise ValueError(
                "Aucun texte détecté. Vérifiez que le PDF contient du texte."
            )

        return text.strip()

    except Exception as e:
        raise ValueError(
            f"Erreur de lecture du PDF : {type(e).__name__}: {e}"
        ) from e


def ask_openai(prompt, max_tokens=700):
    """Generate a response using Ollama Cloud."""

    api_key = os.getenv("OLLAMA_API_KEY")

    if not api_key:
        return (
            "Configuration Error: OLLAMA_API_KEY is missing. "
            "Configure it in Streamlit Cloud Secrets."
        )

    try:
        client = ollama.Client(
            host="https://ollama.com",
            headers={
                "Authorization": f"Bearer {api_key}"
            },
            timeout=180,
        )

        response = client.chat(
            model="gpt-oss:20b-cloud",
            messages=[
                {
                    "role": "user",
                    "content": prompt.strip()
                }
            ],
            options={
                "temperature": 0.4,
                "num_predict": max_tokens,
            },
        )

        content = response.get("message", {}).get("content", "")

        if not isinstance(content, str) or not content.strip():
            return "Ollama Cloud Error: La réponse du modèle est vide."

        return content.strip()

    except Exception as e:
        return f"Ollama Cloud Error: {type(e).__name__}: {e}"

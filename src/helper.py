
import fitz  # PyMuPDF
import ollama


# =========================================================
# EXTRACT TEXT FROM PDF
# =========================================================

def extract_text_from_pdf(uploaded_file):
    """
    Extract readable text from an uploaded PDF.
    """

    if uploaded_file is None:
        raise ValueError("Aucun fichier PDF n'a été fourni.")

    try:
        uploaded_file.seek(0)

        pdf_bytes = uploaded_file.read()

        if not pdf_bytes:
            raise ValueError("Le fichier PDF est vide.")

        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            text_parts = []

            for page in doc:
                page_text = page.get_text("text")

                if page_text:
                    text_parts.append(page_text)

        text = "\n".join(text_parts).strip()

        if not text:
            raise ValueError(
                "Aucun texte détecté dans le PDF. "
                "Le document est peut-être scanné."
            )

        return text

    except Exception as e:
        if isinstance(e, ValueError):
            raise

        raise ValueError(
            f"Impossible de lire le PDF : {type(e).__name__}: {e}"
        ) from e


# =========================================================
# OLLAMA AI
# =========================================================

def ask_openai(prompt, max_tokens=700):
    """
    Generate a response using the local Ollama Mistral model.

    The function name remains ask_openai for compatibility
    with the existing app.py.
    """

    if not isinstance(prompt, str) or not prompt.strip():
        return "Ollama Error: Le prompt est vide."

    try:
        response = ollama.chat(
            model="mistral",
            messages=[
                {
                    "role": "user",
                    "content": prompt.strip()
                }
            ],
            options={
                "temperature": 0.4,
                "num_predict": max_tokens
            }
        )

        # Safely extract the generated text.
        message = response.get("message", {})
        content = message.get("content", "")

        if not isinstance(content, str) or not content.strip():
            return (
                "Ollama Error: Le modèle Mistral a retourné "
                "une réponse vide. Réessayez."
            )

        return content.strip()

    except Exception as e:
        return f"Ollama Error: {type(e).__name__}: {e}"

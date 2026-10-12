import fitz  # PyMuPDF
import ollama


def extract_text_from_pdf(uploaded_file):
    """
    Extracts text from a PDF file.

    Args:
        uploaded_file: Uploaded PDF file from Streamlit

    Returns:
        str: Extracted text from PDF
    """

    doc = fitz.open(
        stream=uploaded_file.read(),
        filetype="pdf"
    )

    text = ""

    for page in doc:
        text += page.get_text()

    return text



def ask_openai(prompt, max_tokens=500):
    """
    Uses Ollama local AI instead of OpenAI API.
    The function name remains ask_openai
    to avoid changing app.py.
    """

    try:

        response = ollama.chat(
            model="mistral",
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

        return f"Ollama Error: {str(e)}"
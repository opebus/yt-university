import logging

from modal import Image, Secret

from yt_university.stub import stub

logger = logging.getLogger(__name__)


image = Image.debian_slim(python_version="3.11").pip_install("openai")


@stub.function(image=image, secrets=[Secret.from_name("university")])
def summarize(text: str):
    """
    Summarize the transcribed text using OpenAI's GPT model.
    """
    import os

    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"Summarize the following text: {text}"
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
        )
        summary = response.choices[0].text.strip()
        return summary
    except Exception as e:
        logger.error(f"Error in summarizing transcription: {str(e)}")
        return "Failed to generate summary."

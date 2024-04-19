import logging

from modal import Image, Secret

from yt_university.stub import stub

logger = logging.getLogger(__name__)

image = Image.debian_slim(python_version="3.11").pip_install("openai")


def create_prompt(text: str) -> str:
    return f"""
        Your task is to provide an in-depth analysis of a provided video transcript, structured to both inform and engage readers. Your narrative should unfold with clarity and insight, reflecting the style of a Paul Graham essay. Follow these major headings for organization:

        # Intro

        Begin with a narrative introduction that captivates the reader, setting the stage for an engaging exploration of bilingualism. Start with an anecdote or a surprising fact to draw in the reader, then succinctly summarize the main themes and objectives of the video.

        # ELI5

        Immediately follow with an ELI5 (Explain Like I'm 5) section. Use simple language and analogies to make complex ideas accessible and engaging, ensuring clarity and simplicity.

        # Terminologies

        - List and define key terminologies mentioned in the video in bullet points. Provide comprehensive yet understandable definitions for someone not familiar with the subject matter. Ensure this section naturally transitions from the ELI5, enriching the reader's understanding without overwhelming them.

        # Summary

        Your summary should unfold as a detailed and engaging narrative essay, deeply exploring the content of the video. This section is the core of your analysis and should be both informative and thought-provoking. When crafting your summary, delve deeply into the video's main themes. Provide a comprehensive analysis of each theme, backed by examples from the video and relevant research in the field. This section should read as a compelling essay, rich in detail and analysis, that not only informs the reader but also stimulates a deeper consideration of the topic's nuances and complexities. Strive for a narrative that is as enriching and engaging as it is enlightening. Please include headings and subheadings to organize your analysis effectively if needed. It should be as detailed and comprehensive as possible.

        # Takeaways

        - End with actionable takeaways in bullet points, offering practical advice or steps based on the video content. These should relate directly to the insights discussed in your essay and highlight their real-world relevance and impact.

        \n\n\nText: {text}
    """


@stub.function(image=image, secrets=[Secret.from_name("university")])
def summarize(text: str):
    """
    Summarize the transcribed text using OpenAI's GPT model.
    """
    import os

    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": create_prompt(text)}],
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        logger.error(f"Error in summarizing transcription: {str(e)}")
        return "Failed to generate summary."

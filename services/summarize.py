import logging

from modal import Image, Secret, Stub

stub = Stub()

logger = logging.getLogger(__name__)

image = Image.debian_slim(python_version="3.11").pip_install("openai")


# reference
# - https://www.reddit.com/r/ChatGPT/comments/11pd2um/the_best_prompt_for_summary_youtube/
def create_prompt(title: str, text: str) -> str:
    return f"""
        Your task is to provide an in-depth analysis of a provided video transcript, structured to both inform and engage readers. Your narrative should unfold with clarity and insight, reflecting the style of a Paul Graham essay.

        First, generate a table of content according to the structure of your essay. This should be the first section.

        Follow these major headings for organization:

        # tl;dr

        Produce a TL;DR that captures the essential points in a concise and informative manner. It should be brief yet comprehensive, providing a clear snapshot of the video's content in a few sentences.
        This summary should enable someone who has not watched the video to understand the key points and takeaways quickly.
        This section should relate well to the rest of the content below.

        # Intro

        Begin with a narrative introduction that captivates the reader, setting the stage for an engaging exploration of bilingualism. Start with an anecdote or a surprising fact to draw in the reader, then succinctly summarize the main themes and objectives of the video.

        # Summary

        Your summary should unfold as a detailed and engaging narrative essay, deeply exploring the content of the video.
        This section is the core of your analysis and should be both informative and thought-provoking.

        When crafting your summary, delve deeply into the video's main themes.
        Provide a comprehensive analysis of each theme, backed by examples from the video and relevant research in the field.

        This section should read as a compelling essay, rich in detail and analysis, that not only informs the reader but also stimulates a deeper consideration of the topic's nuances and complexities.
        Strive for a narrative that is as enriching and engaging as it is enlightening.

        Please include headings and subheadings to organize your analysis effectively if needed. It should be as detailed and comprehensive as possible.

        # Takeaways

        - Conclude with bullet points outlining practical advice or steps derived from the video content.
        These should connect directly to the insights discussed and emphasize their applicability and impact in real-world scenarios.
        - In each of those point, provide some actionable advice or steps that can be taken right away to implement the insights discussed in the video.

        # Terminologies

        List and define key terminologies and acronyms used in the video.
        The definitions should be clear and tailored for readers unfamiliar with the specific jargon.
        This section should follow seamlessly from the ELI5, enhancing understanding without overwhelming the reader.

        Guidelines:
        Ensure that the summary, bullet points, and explanations adhere to a 1500-word limit.
        Despite the constraint, your content should offer a clear and comprehensive understanding of the video's themes and implications.

        Title: {title}
        Text: {text}
    """


@stub.function(
    image=image, secrets=[Secret.from_name("university")], container_idle_timeout=5
)
def generate_summary(title: str, text: str):
    """
    Summarize the transcribed text using OpenAI's GPT model.
    """
    import os

    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": create_prompt(title, text)}],
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        logger.error(f"Error in summarizing transcription: {str(e)}")
        return "Failed to generate summary."


@stub.local_entrypoint()
def main():
    import json

    from dotenv import load_dotenv

    load_dotenv()
    with open("./example.json") as f:
        data = json.load(f)
        summary = generate_summary.local(data["title"], data["transcription"])
        print(summary)

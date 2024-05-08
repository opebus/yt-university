import logging

from chunking import chunk_on_delimiter, tokenize
from openai import OpenAI
from tqdm import tqdm

logger = logging.getLogger(__name__)


def summarize(
    text: str,
    detail: float = 0,
    model: str = "gpt-4-turbo",
    additional_instructions: str | None = None,
    minimum_chunk_size: int | None = 500,
    chunk_delimiter: str = ".",
    summarize_recursively=False,
    verbose=False,
):
    # check detail is set correctly
    assert 0 <= detail <= 1

    # interpolate the number of chunks based to get specified level of detail
    max_chunks = len(chunk_on_delimiter(text, minimum_chunk_size, chunk_delimiter))
    min_chunks = 1
    num_chunks = int(min_chunks + detail * (max_chunks - min_chunks))

    # adjust chunk_size based on interpolated number of chunks
    document_length = len(tokenize(text))
    chunk_size = max(minimum_chunk_size, document_length // num_chunks)
    text_chunks = chunk_on_delimiter(text, chunk_size, chunk_delimiter)
    if verbose:
        print(f"Splitting the text into {len(text_chunks)} chunks to be summarized.")
        print(f"Chunk lengths are {[len(tokenize(x)) for x in text_chunks]}")

    # set system message
    system_message_content = "Rewrite this text in summarized form"
    if additional_instructions is not None:
        system_message_content += f"\n\n{additional_instructions}"

    accumulated_summaries = []
    for chunk in tqdm(text_chunks):
        if summarize_recursively and accumulated_summaries:
            accumulated_summaries_string = "\n\n".join(accumulated_summaries)
            user_message_content = f"Previous summaries:\n\n{accumulated_summaries_string}\n\nText to summarize next:\n\n{chunk}"
        else:
            user_message_content = chunk

        messages = [
            {"role": "system", "content": system_message_content},
            {"role": "user", "content": user_message_content},
        ]

        client = OpenAI(api_key=".")

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
            )
            summary = response.choices[0].message.content.strip()
            accumulated_summaries.append(summary)
        except Exception as e:
            logger.error(f"Error in summarizing transcription: {str(e)}")
            return "Failed to generate summary."

    # Compile final summary from partial summaries
    final_summary = "\n\n".join(accumulated_summaries)

    return final_summary


import json


def combine_text_from_file(file_path):
    with open(file_path) as file:
        data = json.load(file)  # Load data from JSON file

    combined_text = ""
    for chunk in data["chunks"]:  # Loop through each chunk
        combined_text += chunk["text"]  # Append the text from each chunk

    return combined_text


def create_prompt(title: str, text: str) -> str:
    return f"""
        Your task is to provide an in-depth analysis of the provided transcript, structured to both inform and engage readers.
        Your narrative should unfold with clarity and insight, reflecting the style of a Paul Graham essay.

        Your summary should unfold as a detailed and engaging narrative essay, deeply exploring the content.
        This section is the core of your analysis and should be both informative and thought-provoking.

        When crafting your summary, delve deeply into the main themes of the transcript with title {title}
        Provide a comprehensive analysis of each theme, backed by examples from the video and relevant research in the field.

        This section should read as a compelling essay, rich in detail and analysis, that not only informs the reader but also stimulates a deeper consideration of the topic's nuances and complexities.
        Strive for a narrative that is as enriching and engaging as it is enlightening.

        Use markdown to format your text effectively. Return only the main themes without any introduction or conclusion.

        Text: {text}
    """


def final(text):
    client = OpenAI(api_key=".")

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "user",
                    "content": create_prompt(
                        "Yann Lecun: Meta AI, Open Source, Limits of LLMs, AGI & the Future of AI | Lex Fridman Podcast #416",
                        text,
                    ),
                }
            ],
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        logger.error(f"Error in summarizing transcription: {str(e)}")
        return "Failed to generate summary."


asd = """
The number of registrations for visa spots has dramatically increased over the past decade, resulting in a highly competitive lottery system that fails to consider the skills and qualifications of the applicants. Despite there being only 65,000 spots available last year, 780,000 people registered, highlighting a flawed system where most candidates are unlikely to secure a visa. This has prompted more serious consideration of America's immigration policies. In the podcast hosted by Molly O'Shea, founder of Sorcery, Min Kim, the founder of Lighthouse, shares her journey from a career in New York's financial services to establishing her own company in San Francisco, aimed at providing an efficient immigration solution for technology pioneers. Min's career transition was influenced by her desire to meet inspiring founders and her interactions with influential figures in the tech industry, eventually leading to her relocation to San Francisco and the founding of Lighthouse, a platform facilitating U.S. work visa applications for the tech community.

Min Kim transitioned from a career in financial services in New York to tech in San Francisco, initially investing in AI and robotics, before moving to a startup where she launched a global accelerator for international entrepreneurs. Inspired by these experiences, Kim founded Lighthouse, a platform aimed at streamlining the U.S. high-skilled immigration process. Lighthouse seeks to democratize access to high-skilled immigration, addressing the cumbersome bureaucratic processes that inhibit the world’s most talented individuals from contributing to the U.S. technology sector, which is a major driver of the country’s economic and cultural prowess. Kim’s mission with Lighthouse is to simplify these processes, similar to how other services have streamlined tasks like tax filing and company incorporation online.

The U.S. created specialty occupation visa categories in 1990, like the H-1B visa, to attract and employ foreign nationals in specific roles, including technology and consulting, with an annual cap of 65,000 visas. Over the years, the demand has dramatically exceeded this cap; for example, 780,000 people registered for the same 65,000 spots last year. This situation results in many skilled individuals being subjected to a lottery system that doesn’t consider their qualifications, leading to a high probability of rejection.

Similarly, the green card system is overwhelmed, with only 250,000 issued annually versus demand from millions seeking permanent residency, causing severe backlogs and disproportionately affecting people from certain countries. As countries like Canada, the UK, and Australia make efforts to attract global talent through more accessible immigration processes, the U.S. faces increased competition to remain the preferred destination for skilled individuals. The current system, mainly hinging on employer sponsorship and beset by widespread misconceptions and a lack of public understanding, underscores the need for significant immigration reform to effectively leverage global talent.

The U.S. immigration system requires applicants to have a bachelor's degree or equivalent work experience, and their role must align with specific categories tied to employer sponsorship, like those defined under the TN or H-1B visa classifications. Over the past two years, the Biden administration has recognized a shortfall in supporting STEM talent leading to a more focused campaign to retain this group within the country. However, the immigration law sector, mainly made up of boutique law firms and a few major firms, often experiences information asymmetry. Lawyers are not typically incentivized to offer innovative or alternative solutions to applicants, who generally receive generic advice, pushing them into the highly competitive H-1B visa lottery with low success rates.

Consequently, individuals often seek advice from peers and alternative paths like the O-1, J-1 visas, or the STEM OPT extension, which have been underused but are now being promoted by recent initiatives. This marks a shift from older methods driven by the tech industry to push for substantial policy reforms in immigration, spotlighting the need for more accessible and varied pathways for immigration to harness global technical talent effectively.

The O-1 visa, often underutilized and known as the "Einstein visa," presents a significant opportunity for high-skilled immigrants, particularly in the U.S. technology sector. Despite its potential, it remains relatively obscure due to stringent qualifications projected on official platforms, such as requiring internationally recognized awards. However, the reality is that qualifications for the O-1 visa are more accessible than commonly perceived. This visa doesn't mandate minimum education levels or specified wage levels, can be renewed indefinitely, and isn't limited by country quotas. Currently, only about 10,000 applications are filed annually, with less than half from STEM fields, despite there being no cap on the number of O-1 visas that can be issued. Min Kim's company, Lighthouse, focuses largely on facilitating O-1 visas, aiming to increase the number of these visas tenfold. This shift recognizes the need for elevating the awareness and usage of such visa categories to tap into global talent effectively, comparable to how certain industries have leveraged it for bringing talents like athletes and entertainers to the U.S.

The West Coast, particularly the Bay Area, is currently experiencing a significant hard tech boom. Economic agglomeration effects are contributing to a virtuous cycle where a dense population of smart, productive people attracts more talent due to community network effects. Despite a belief in the potential of emerging startup ecosystems worldwide, the distinct characteristics of the Bay Area still make it a unique hub for high-tech industries and talented professionals. This dynamic is driving progress and creating numerous jobs, attracting top AI and robotics talent from organizations like DeepMind and OpenAI.

Regarding the platform Lighthouse, founded by a former investor in AI and robotics, it is designed to address the inefficiencies in visa processing for highly skilled individuals. Lighthouse aims to simplify the complicated but tractable problem of navigating the U.S. immigration system, which is often slow and confusing, providing a miserable user experience. The platform focuses on building a user-friendly experience, with 30% visible to users ensuring ease of use and 70% of the operations under the hood, streamlining the processing and keeping users informed on the status and requirements of their applications without the need to engage extensively with attorneys or navigate cumbersome communication. This approach makes the visa process more efficient and scalable, significantly enhancing customer experience.

Min Kim discusses the integration of AI and operational processes in visa applications, which historically involved lawyers and legal staff. By leveraging AI, her team can efficiently summarize extensive research and refine applications to meet governmental standards. This integration reduces the mundane tasks associated with traditional application preparation, such as compiling lengthy documents, thus saving time and legal costs. This efficiency allows her team more time to interact with clients and focus on providing quality service that ensures trust. Moreover, advancements in digital processes by USCIS, like online H-1B registration and premium processing options, have significantly sped up the approval timeline, allowing applicants to receive outcomes within 15 days for certain visa categories, improving overall efficiency and reducing stress for applicants.

Min Kim is enthusiastic about the potential for expanding and enhancing Lighthouse, the platform she founded to streamline the process for highly skilled individuals seeking U.S. visas. A key focus for the near future involves establishing core partnerships with organizations like OnDeck and HFZero, which are already attracting significant talent, to further extend Lighthouse’s reach. She also foresees transforming Lighthouse into a full-stack legal services company, not just guiding clients on visa acquisition but also on employment law and compliance issues for businesses hiring foreign nationals.

One innovative feature envisioned for Lighthouse is integrating visa eligibility directly into Applicant Tracking Systems (ATS), allowing recruiters to easily identify candidates' visa qualifications. This would simplify and demystify the visa process for fast-growing companies that often view immigration as a complex and burdensome issue. Over the coming year, Lighthouse aims to grow its client base significantly, hoping to serve around a thousand individuals with their visa and immigration needs. The platform, backed by a team with expertise in engineering, operations, and legal matters, is currently handling numerous clients and has a substantial waitlist, indicating strong demand for its services.

Min Kim reflects on her career path, noting that significant barriers like financial support, community connections, and immigration laws have shaped her journey. She mentions that her work across different companies always circled back to tackling these obstacles, culminating in her focus on simplifying the immigration process through her platform, Lighthouse. Min, an immigrant herself, highlights the lengthy process of becoming a U.S. citizen, which she views as a quintessential American experience—choosing to be part of the nation and helping others achieve the same.

Regarding life in San Francisco, Min finds it uniquely suited for individuals who are ambitious and possess a quirky or unconventional character, describing it as the perfect place for someone who matches that description. Although she loves visiting her family in South Korea and Japan, and acknowledges the cultural richness of these countries, she feels deeply rooted in California despite its high cost of living. Min appreciates San Francisco's distinct vibe and doesn't see herself living elsewhere, having fully adapted to the Californian lifestyle.

This segment reveals the engaging social and professional environment of San Francisco, where people often engage in intellectual discussions and encounter notable figures like Sam Altman without much fanfare, reflecting a cultural approach to celebrity that differs from places like New York. The discussion delves into how areas like Silicon Valley are starting to recognize and utilize visas like the O-1, previously favored by Hollywood. It also captures the dynamic, rapidly evolving tech landscape in Silicon Valley, marked by significant advancements and investments in sectors like space exploration and autonomous driving. Key entrepreneurial figures in emerging hard tech sectors are highlighted for driving monumental industry shifts. The conversation concludes with an overview of Min Kim's goals for Lighthouse, focusing on expansion and recruitment to meet the growing demand for its services aimed at facilitating visa processes for skilled individuals in the tech industry.

Min Kim is focusing on expanding her platform, Lighthouse, which aims to streamline the visa process for highly skilled individuals. The company's growth strategy over the next 6 to 12 months includes forming significant partnerships with organizations like OnDeck. Moreover, Kim encourages individuals starting or joining new ventures who require visa assistance to contact Lighthouse, as their early involvement offers insights into future market needs, which could be beneficial for investors as well. She expresses gratitude for the success and recognition Lighthouse has received, emphasizing its role in democratizing skilled immigration and benefiting both the U.S. and the tech industry at large.

"""
if __name__ == "__main__":
    # text = combine_text_from_file("short.json")
    # print(summarize(text, detail=0.5, verbose=True, summarize_recursively=True))
    final_text = final(asd)
    print(final_text)

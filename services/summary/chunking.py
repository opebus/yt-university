import logging

import tiktoken

logger = logging.getLogger(__name__)


def tokenize(text: str) -> list[str]:
    encoding = tiktoken.encoding_for_model("gpt-4-turbo")
    return encoding.encode(text)


def chunk_on_delimiter(input: str, max_tokens: int, delimiter: str) -> list[str]:
    chunks = input.split(delimiter)
    combined_chunks, _, dropped_chunk_content = combine_chunks_no_minimum(
        chunks, max_tokens, chunk_delimiter=delimiter, add_ellipsis_for_overflow=True
    )
    if dropped_chunk_content > 0:
        logger.warning(f"{dropped_chunk_content} chunks were dropped due to overflow")
    return combined_chunks


def combine_chunks_no_minimum(
    chunks: list[str],
    max_tokens: int,
    chunk_delimiter: str = "\n\n",
    header: str | None = None,
    add_ellipsis_for_overflow: bool = False,
) -> tuple[list[str], list[int]]:
    dropped_chunk_count = 0

    output = []
    output_indices = []

    candidate = [] if header is None else [header]
    candidate_indices = []
    for chunk_i, chunk in enumerate(chunks):
        chunk_with_header = [chunk] if header is None else [header, chunk]
        if len(tokenize(chunk_delimiter.join(chunk_with_header))) > max_tokens:
            logger.warning("chunk overflow")
            if (
                add_ellipsis_for_overflow
                and len(tokenize(chunk_delimiter.join(candidate + ["..."])))
                <= max_tokens
            ):
                candidate.append("...")
                dropped_chunk_count += 1
            continue  # this case would break downstream assumptions
        # estimate token count with the current chunk added
        extended_candidate_token_count = len(
            tokenize(chunk_delimiter.join(candidate + [chunk]))
        )
        # If the token count exceeds max_tokens, add the current candidate to output and start a new candidate
        if extended_candidate_token_count > max_tokens:
            output.append(chunk_delimiter.join(candidate))
            output_indices.append(candidate_indices)
            candidate = chunk_with_header  # re-initialize candidate
            candidate_indices = [chunk_i]
        # otherwise keep extending the candidate
        else:
            candidate.append(chunk)
            candidate_indices.append(chunk_i)

    # add the remaining candidate to output if it's not empty
    if (header is not None and len(candidate) > 1) or (
        header is None and len(candidate) > 0
    ):
        output.append(chunk_delimiter.join(candidate))
        output_indices.append(candidate_indices)
    return output, output_indices, dropped_chunk_count

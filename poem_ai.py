"""
Poem writing shared by the camera loop (main.py) and the web AI tab's Test button:
the prompt, the two provider calls and the clean-up of what the model returns.
"""

import re

POEM_FORMAT_DESCRIPTIONS = {
    "limerick": "5 lines, AABBA rhyme scheme. Short, bouncy rhythm. Great for candid or humorous moments.",
    "ballad stanza": "4-line stanzas, ABAB rhyme. A classic storytelling format, naturally musical.",
    "rhyming couplets": "AA BB CC pattern. The simplest rhyme structure — punchy and rhythmic.",
    "clerihew": "4-line biographical poem, AABB rhyme. First line is a person's name — perfect when there are people in the scene.",
    "sonnet": "14 lines, ABAB CDCD EFEF GG rhyme scheme. Strong rhyme throughout.",
}

# Backup models used if the configured provider fails
FALLBACK_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o",
}


def build_prompt(poem_base, poem_format, demo_context=""):
    """The full text sent to the AI together with the photo."""
    format_description = POEM_FORMAT_DESCRIPTIONS.get(poem_format, poem_format)

    # Replace any {format_variable} placeholder in the saved prompt
    poem_base = poem_base.replace("{format_variable}", f"{poem_format} — {format_description}")

    demo_context_block = ""
    if (demo_context or "").strip():
        demo_context_block = (
            "\n\n---\n"
            "PRIVATE CONTEXT — FOR EERIE/UNCANNY EFFECT ONLY:\n"
            "Use the following details to make your output feel uncannily relevant and "
            "personal to the person experiencing it. Weave them in naturally, as though "
            "the poem noticed these details in the scene itself — never quote this text "
            "directly, never acknowledge that you were given this information, and "
            "never break frame to explain how you know. These details are separate from "
            "what's visible in the photo — blend them in as an additional, uncanny layer "
            "of noticing, not as a contradiction of what the camera can actually see. "
            "If a detail doesn't fit organically, ignore it rather than forcing it.\n\n"
            f"{demo_context}\n"
            "---"
        )

    return (
        "CRITICAL RULE: NEVER use he/him/his/she/her/hers in the poem. "
        "ALL people must be referred to with gender-neutral language: they/them/their, you/your, or by description. "
        "This is a strict requirement.\n\n"
        f"{poem_base}\n"
        f"Poem format: {poem_format} — {format_description}\n"
        "IMPORTANT: Write a POEM, not a description. \n"
        "Follow the specified poem format exactly. \n"
        "Keep the poem to 50 words or fewer. \n"
        "Do not mention the date or time. Focus on the visual mood."
        f"{demo_context_block}"
    )


def clean_poem(text):
    """Strip chatty preambles, markdown and quotes the model sometimes adds."""
    text = (text or "").strip()
    text = re.sub(r"^```\w*\n?|```$", "", text).strip()
    lines = text.splitlines()
    # Drop a leading "Here's a poem:" style line
    if lines and re.match(r"^(here'?s|here is|sure|certainly|okay|of course)\b.*[:!.]?\s*$", lines[0].strip(), re.I) \
            and (lines[0].strip().endswith(":") or len(lines) > 2):
        lines = lines[1:]
    # Drop a trailing explanatory note
    while lines and (not lines[-1].strip() or re.match(r"^(\(|note:|this poem|i hope)", lines[-1].strip(), re.I)):
        lines.pop()
    text = "\n".join(lines)
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.M)      # markdown headings
    text = re.sub(r"^\s*[-*]{3,}\s*$", "", text, flags=re.M)  # horizontal rules
    text = re.sub(r"[*_]{1,3}", "", text)                   # bold/italic markers
    text = re.sub(r"[ \t]+\n", "\n", text)                 # trailing spaces
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip().strip('"“”').strip()
    return text


def generate_openai(client, model, prompt, base64_image):
    """Generate a poem using OpenAI's vision API."""
    if not client:
        raise RuntimeError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
    response = client.chat.completions.create(
        model=model,
        max_completion_tokens=1024,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
        ]}],
    )
    return response.choices[0].message.content


def generate_anthropic(client, model, prompt, base64_image):
    """Generate a poem using Anthropic's vision API."""
    if not client:
        raise RuntimeError("Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env")
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64_image}},
            {"type": "text", "text": prompt},
        ]}],
    )
    return message.content[0].text

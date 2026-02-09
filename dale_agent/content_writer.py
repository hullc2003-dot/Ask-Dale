class ContentWriter:
    """
    Writes a 1500‑word digital nomad affiliate marketing article.

    You inject your LLM client when you instantiate this class.
    """

    def __init__(self, llm_client):
        self.llm = llm_client

    async def write_article(self, topic: str, target_length: int) -> str:
        prompt = (
            f"Write a {target_length}-word article about {topic}. "
            "Make it structured, detailed, and optimized for SEO."
        )
        return await self.llm(prompt)

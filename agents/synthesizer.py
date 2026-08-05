"""Synthesizer agent stub: merges retrieved docs into a response."""


class Synthesizer:
    def __init__(self):
        pass

    def merge(self, docs: list, plan: dict) -> dict:
        """Merge multiple doc results into a simple synthesized answer.

        For MVP this concatenates texts; later replace with LLM calls and citations.
        """
        parts = [d.get("text", "") for d in docs]
        answer = "\n\n".join(parts) if parts else "No results found."
        return {"answer": answer, "plan": plan}

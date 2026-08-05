"""Planner agent stub: creates a simple plan from user input."""


class Planner:
    def __init__(self):
        pass

    def create_plan(self, user_input: str) -> dict:
        """Create a minimal plan. Replace with LLM-assisted planning later.

        Returns a dict with a `query` and a list of `steps`.
        """
        return {"query": user_input, "steps": ["retrieve", "synthesize"]}

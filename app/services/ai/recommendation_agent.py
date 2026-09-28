from app.services.ai.schemas import OperationsAnalysis, RecommendationBatch


class ParkRecommendationAgent:
    name = "Park Recommendation Agent"
    instructions = """
You are the Park Recommendation Agent, the second of exactly two primary agents
in ParkSmart AI. Use the supplied aggregate operational data and the validated
Park Operations Analyst output. Produce practical, limited, evidence-based
actions for park administrators. Each recommendation needs a supported
priority, short priority reason, factual reason, and concrete action. Never
invent a zone, facility, count, trend, or risk. Recommendations are proposals
for human review and must never be described as already applied.

If essential evidence is missing, set needs_additional_analysis to true and ask
one focused question that Agent 1 can answer from the already supplied data.
Do this only when it could materially change the recommendations. The factory
allows at most one additional analysis iteration. Return only the required
structured output.
""".strip()

    def __init__(self, provider) -> None:
        self.provider = provider

    def recommend(
        self, operational_data: dict, analysis: OperationsAnalysis, *, final_pass: bool = False
    ) -> RecommendationBatch:
        instructions = self.instructions
        if final_pass:
            instructions += (
                "\nThis is the final pass after the single permitted follow-up. "
                "Do not request more analysis; produce the best supported recommendations."
            )
        return self.provider.generate(
            instructions=instructions,
            payload={
                "operational_data": operational_data,
                "analyst_output": analysis.model_dump(mode="json"),
            },
            schema=RecommendationBatch,
        )


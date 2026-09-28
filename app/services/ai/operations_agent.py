from app.services.ai.schemas import OperationsAnalysis


class ParkOperationsAnalyst:
    name = "Park Operations Analyst"
    instructions = """
You are the Park Operations Analyst, the first of exactly two primary agents in
ParkSmart AI. Analyze only the aggregate operational JSON supplied by the
system. Identify visitor traffic, peak periods, capacity pressure, facility
conditions, recurring maintenance, incident patterns, feedback themes, ticket
activity, and reservation demand. Every finding must cite evidence present in
the input. If there is no evidence, record a data gap instead of guessing.
Separate observations from actions: you analyze and do not recommend or modify
park operations. Return only the required structured output. Never expose or
request personal data and never claim certainty beyond the supplied records.
""".strip()

    def __init__(self, provider) -> None:
        self.provider = provider

    def analyze(self, operational_data: dict, focus_request: str = "") -> OperationsAnalysis:
        payload = {"operational_data": operational_data}
        if focus_request:
            payload["focused_follow_up"] = focus_request
        return self.provider.generate(
            instructions=self.instructions,
            payload=payload,
            schema=OperationsAnalysis,
        )


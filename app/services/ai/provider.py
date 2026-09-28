from __future__ import annotations

import json
from typing import TypeVar

from flask import current_app
from openai import OpenAI
from pydantic import BaseModel


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class AIProviderError(RuntimeError):
    pass


class OpenAIProvider:
    """Server-side structured output adapter; business services never import the SDK."""

    def __init__(self) -> None:
        api_key = current_app.config.get("OPENAI_API_KEY", "")
        if not api_key:
            raise AIProviderError("OPENAI_API_KEY is not configured.")
        self.model = current_app.config["OPENAI_MODEL"]
        self.max_output_tokens = current_app.config["OPENAI_MAX_OUTPUT_TOKENS"]
        self.client = OpenAI(
            api_key=api_key,
            timeout=current_app.config["OPENAI_TIMEOUT_SECONDS"],
            max_retries=1,
        )

    def generate(self, *, instructions: str, payload: dict, schema: type[SchemaT]) -> SchemaT:
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": instructions},
                    {
                        "role": "user",
                        "content": "Analyze only this supplied JSON:\n"
                        + json.dumps(payload, separators=(",", ":"), default=str),
                    },
                ],
                text_format=schema,
                max_output_tokens=self.max_output_tokens,
                store=False,
            )
        except Exception as exc:  # SDK errors are normalized at this boundary.
            raise AIProviderError(f"OpenAI request failed: {type(exc).__name__}") from exc

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise AIProviderError("OpenAI returned no validated structured output.")
        return parsed


"""Hosted LLM factory for Ghost.

Two providers: Anthropic + OpenAI (also handles "custom OpenAI-compatible"
by setting base_url). Each exposes a unified `tool_use_loop` interface
that handles parallel tool calls and returns the full transcript with
token + cost metadata.

Local is intentionally not supported here -- the plan locks Ghost to
hosted-only for now. The settings layer rejects mode='local' at write time.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ghost import settings as ghost_settings

logger = logging.getLogger(__name__)


# Approximate per-1k-token prices (USD). Kept conservative so the cost
# preview doesn't under-quote. Updated alongside model launches.
PRICING_PER_1K = {
    # Anthropic
    "claude-opus-4-7": {"input": 0.015, "output": 0.075},
    "claude-opus-4-6": {"input": 0.015, "output": 0.075},
    "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5-20251001": {"input": 0.0008, "output": 0.004},
    # OpenAI
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4.1": {"input": 0.005, "output": 0.015},
    "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016},
}

DEFAULT_PRICE = {"input": 0.001, "output": 0.003}


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    price = PRICING_PER_1K.get(model, DEFAULT_PRICE)
    return round(
        (tokens_in / 1000.0) * price["input"]
        + (tokens_out / 1000.0) * price["output"],
        4,
    )


# ---------------------------------------------------------------------------
# Tool-use loop result
# ---------------------------------------------------------------------------


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    result: Any = None
    error: Optional[str] = None


@dataclass
class LoopResult:
    answer: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = ""

    def cost_usd(self) -> float:
        return estimate_cost_usd(self.model, self.tokens_in, self.tokens_out)


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------


class GhostLLM:
    """Provider-agnostic interface used by the Ghost agent."""

    name = "abstract"

    def __init__(self, *, api_key: str, model: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def run_tool_use_loop(
        self,
        *,
        system: str,
        user: str,
        tools: list[dict[str, Any]],
        tool_handler: Callable[[str, dict[str, Any]], Any],
        max_iterations: int = 8,
    ) -> LoopResult:
        raise NotImplementedError


def get_llm(*, override_model: Optional[str] = None) -> GhostLLM:
    """Return a configured GhostLLM. Raises if settings are incomplete."""
    s = ghost_settings.get()
    if s["mode"] != "hosted":
        raise RuntimeError(
            "Local Ghost is not yet available. Switch to hosted in settings."
        )
    key = ghost_settings.get_api_key()
    if not key:
        raise RuntimeError(
            "No API key configured. Set one in Settings → Ghost."
        )
    model = override_model or s["model"]
    provider = s["provider"]
    base_url = s.get("base_url")
    if provider == "anthropic":
        return AnthropicGhostLLM(api_key=key, model=model)
    if provider in ("openai", "custom"):
        return OpenAIGhostLLM(api_key=key, model=model, base_url=base_url)
    raise RuntimeError(f"Unknown provider: {provider!r}")


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------


class AnthropicGhostLLM(GhostLLM):
    name = "anthropic"

    def run_tool_use_loop(
        self,
        *,
        system: str,
        user: str,
        tools: list[dict[str, Any]],
        tool_handler: Callable[[str, dict[str, Any]], Any],
        max_iterations: int = 8,
    ) -> LoopResult:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        # Convert OpenAI-style tools schema to Anthropic's. They differ:
        # Anthropic wants {name, description, input_schema}.
        a_tools = [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t["parameters"],
            }
            for t in tools
        ]
        messages: list[dict[str, Any]] = [{"role": "user", "content": user}]
        loop_tool_calls: list[ToolCall] = []
        tokens_in = 0
        tokens_out = 0

        for _ in range(max_iterations):
            response = client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system,
                tools=a_tools,
                messages=messages,
            )
            tokens_in += getattr(response.usage, "input_tokens", 0) or 0
            tokens_out += getattr(response.usage, "output_tokens", 0) or 0

            if response.stop_reason == "tool_use":
                # Collect all tool_use blocks (model may emit parallel calls).
                tool_uses = [b for b in response.content if b.type == "tool_use"]
                assistant_content = list(response.content)
                messages.append({"role": "assistant", "content": assistant_content})
                tool_results: list[dict[str, Any]] = []
                for tu in tool_uses:
                    tc = ToolCall(name=tu.name, arguments=dict(tu.input))
                    try:
                        tc.result = tool_handler(tu.name, tc.arguments)
                    except Exception as exc:
                        tc.error = str(exc)
                        tc.result = {"error": str(exc)}
                    loop_tool_calls.append(tc)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": json.dumps(tc.result, default=str),
                    })
                messages.append({"role": "user", "content": tool_results})
                continue

            # Final answer.
            answer_parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
            return LoopResult(
                answer="\n".join(answer_parts).strip(),
                tool_calls=loop_tool_calls,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                model=self.model,
            )
        # Hit iteration cap.
        return LoopResult(
            answer="(Reached tool-use iteration cap without producing a final answer.)",
            tool_calls=loop_tool_calls,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=self.model,
        )


# ---------------------------------------------------------------------------
# OpenAI / OpenAI-compatible
# ---------------------------------------------------------------------------


class OpenAIGhostLLM(GhostLLM):
    name = "openai"

    def run_tool_use_loop(
        self,
        *,
        system: str,
        user: str,
        tools: list[dict[str, Any]],
        tool_handler: Callable[[str, dict[str, Any]], Any],
        max_iterations: int = 8,
    ) -> LoopResult:
        from openai import OpenAI

        kwargs: dict[str, Any] = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = OpenAI(**kwargs)

        oai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t["parameters"],
                },
            }
            for t in tools
        ]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        loop_tool_calls: list[ToolCall] = []
        tokens_in = 0
        tokens_out = 0

        for _ in range(max_iterations):
            response = client.chat.completions.create(
                model=self.model,
                tools=oai_tools,
                messages=messages,
                max_tokens=2048,
            )
            usage = getattr(response, "usage", None)
            if usage is not None:
                tokens_in += getattr(usage, "prompt_tokens", 0) or 0
                tokens_out += getattr(usage, "completion_tokens", 0) or 0
            choice = response.choices[0]
            msg = choice.message
            if msg.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    args = json.loads(tc.function.arguments or "{}")
                    call = ToolCall(name=tc.function.name, arguments=args)
                    try:
                        call.result = tool_handler(call.name, call.arguments)
                    except Exception as exc:
                        call.error = str(exc)
                        call.result = {"error": str(exc)}
                    loop_tool_calls.append(call)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(call.result, default=str),
                    })
                continue

            return LoopResult(
                answer=(msg.content or "").strip(),
                tool_calls=loop_tool_calls,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                model=self.model,
            )

        return LoopResult(
            answer="(Reached tool-use iteration cap without producing a final answer.)",
            tool_calls=loop_tool_calls,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=self.model,
        )

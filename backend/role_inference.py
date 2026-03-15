"""Automatic speaker role inference using the shared LLM instance.

Runs immediately after STT. Assigns a concise meeting role (e.g. "Project
Manager", "Lead Developer") to each speaker based on their utterances.
The result is stored as role field on each speaker stats entry in the
existing result JSON blob — no schema migration required.
"""

import json
import logging
from typing import Any

from storage import get_job, update_job

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt & schema
# ---------------------------------------------------------------------------

ROLE_SYSTEM_PROMPT = """You are a meeting analyst. Your task is to assign a concise professional role to each meeting participant based on what they say.

For each speaker, read their sample utterances and decide:
- What role or function does this person likely have in the organisation?
- Express the role in 2-4 words (e.g. "Project Manager", "Lead Developer", "UX Designer", "QA Engineer", "Client Stakeholder", "Product Owner", "Data Scientist").

Rules:
- Only use information present in the provided utterances
- Keep each role label short and professional (2-4 words maximum)
- If a role genuinely cannot be determined from the sample, use "Meeting Participant"
- Do NOT invent roles that have no basis in the transcript
- Return JSON only, matching the provided schema exactly"""

ROLE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "roles": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        }
    },
    "required": ["roles"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_speaker_samples(
    segments: list[dict[str, Any]],
    max_per_speaker: int = 8,
) -> dict[str, list[str]]:
    """Collect up to max_per_speaker utterances per speaker from the transcript.

    Takes the first half and last half of the available utterances so we get
    a representative spread across the meeting without sending too many tokens.
    """
    raw: dict[str, list[str]] = {}
    for seg in segments:
        speaker = seg.get("speaker", "Unknown")
        text = seg.get("text", "").strip()
        if text:
            raw.setdefault(speaker, []).append(text)

    sampled: dict[str, list[str]] = {}
    for speaker, utterances in raw.items():
        if len(utterances) <= max_per_speaker:
            sampled[speaker] = utterances
        else:
            half = max_per_speaker // 2
            sampled[speaker] = utterances[:half] + utterances[-half:]

    return sampled


def _format_samples_for_prompt(samples: dict[str, list[str]]) -> str:
    """Format speaker samples as a readable prompt block."""
    sections: list[str] = []
    for speaker, utterances in samples.items():
        lines = [f"**{speaker}**:"]
        for utt in utterances:
            lines.append(f'  - "{utt}"')
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_role_inference(job_id: str, app_state: object) -> None:
    """Infer and persist meeting roles for each speaker in a completed transcript.

    Reads speaker utterances from storage, prompts the LLM for role labels,
    and writes the roles back into result.speakers[].role via update_job.

    This function is intentionally non-fatal: if inference fails the caller
    should log and continue — roles are a nice-to-have, not critical.
    """
    job = get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    result = job.get("result")
    if result is None:
        raise ValueError(f"Job {job_id} has no transcript result")

    segments = result.get("segments", [])
    speakers_stats = result.get("speakers", [])

    if not segments or not speakers_stats:
        logger.info("Job %s has no segments/speakers; skipping role inference", job_id)
        return

    samples = _build_speaker_samples(segments)
    samples_text = _format_samples_for_prompt(samples)

    speaker_names = [s["label"] for s in speakers_stats]
    speaker_list = ", ".join(speaker_names)

    messages = [
        {"role": "system", "content": ROLE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Speakers in this meeting: {speaker_list}\n\n"
                f"Sample utterances per speaker:\n\n{samples_text}\n\n"
                "Assign a professional role to each speaker. "
                'Return JSON: {"roles": {"Speaker 1": "Role", ...}}'
            ),
        },
    ]

    response = app_state.llm.create_chat_completion(
        messages=messages,
        response_format={"type": "json_object", "schema": ROLE_SCHEMA},
        temperature=0.1,
        max_tokens=256,
    )

    raw_text = response["choices"][0]["message"]["content"]
    parsed = json.loads(raw_text)
    roles: dict[str, str] = parsed.get("roles", {})

    if not roles:
        logger.warning("Job %s: LLM returned empty roles dict", job_id)
        return

    # Write roles into the speaker stats entries
    updated = False
    for spk in speakers_stats:
        label = spk.get("label", "")
        if label in roles:
            spk["role"] = roles[label].strip()
            updated = True

    if updated:
        update_job(job_id, result=result)
        logger.info(
            "Job %s: assigned roles %s",
            job_id,
            {s["label"]: s.get("role") for s in speakers_stats},
        )

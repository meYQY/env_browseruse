import json
import os
import time

from .base import LLMProvider


class KimiProvider(LLMProvider):
    def __init__(
        self,
        api_key=None,
        base_url=None,
        model=None,
        temperature=0.3,
        max_retries=3,
    ):
        self.api_key = api_key or os.environ.get("KIMI_API_KEY", "")
        self.base_url = base_url or os.environ.get(
            "KIMI_BASE_URL", "https://api.moonshot.cn/v1"
        )
        self.model = model or os.environ.get("KIMI_MODEL", "kimi-k2.6")
        self.temperature = temperature
        self.max_retries = max_retries

    # ------------------------------------------------------------------
    # Internal API call
    # ------------------------------------------------------------------

    def _call_api(self, messages: list, temperature: float = None) -> str:
        """Call Kimi API using requests (not openai SDK to minimize deps).

        Uses the OpenAI-compatible ``/chat/completions`` endpoint with retry
        logic and exponential back-off for transient failures.
        """
        import requests

        if not self.api_key:
            raise RuntimeError(
                "Kimi API key is not set. Provide it via the api_key parameter "
                "or the KIMI_API_KEY environment variable."
            )

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
        }

        last_exc = None
        for attempt in range(self.max_retries):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=(15, 120))

                # Do not retry client errors (4xx) except 429 rate-limit
                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    resp.raise_for_status()

                # Retry on 429 and 5xx
                if resp.status_code == 429 or resp.status_code >= 500:
                    resp.raise_for_status()

                # Success path
                data = resp.json()
                return data["choices"][0]["message"]["content"]

            except Exception as exc:
                last_exc = exc
                # Only retry on network / transient server errors
                if (
                    isinstance(exc, requests.exceptions.HTTPError)
                    and exc.response is not None
                    and 400 <= exc.response.status_code < 500
                    and exc.response.status_code != 429
                ):
                    raise  # non-retryable client error
                if attempt < self.max_retries - 1:
                    wait = 2**attempt  # 1s, 2s, 4s …
                    time.sleep(wait)

        raise RuntimeError(
            f"Kimi API call failed after {self.max_retries} retries"
        ) from last_exc

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_instruction(self, structured_task: dict) -> str:
        """Convert a structured task spec into a clear user-facing instruction."""
        system_msg = (
            "You write realistic user instructions for browser-use benchmark tasks. "
            "You receive a structured task spec as JSON. Your job is ONLY to verbalize "
            "that spec as one natural instruction a human might give to a browser agent.\n\n"
            "Hard constraints:\n"
            "- Preserve every target clue, action, required value, and quoted phrase exactly.\n"
            "- Do not invent entities, facts, actions, constraints, labels, ratings, quantities, "
            "titles, comments, or expected outcomes.\n"
            "- Do not decide ground truth or verifier logic.\n"
            "- Do not mention internal fields such as task_id, entity_id, target_entity, "
            "target_entities, action type names, JSON keys, verifier, or ground truth.\n"
            "- Do NOT use internal target labels like 'target A', 'target B', 'issue A', "
            "'product B', etc. Refer to each entity by its natural attributes, e.g. "
            "'the issue titled X', 'product named Y', 'issue #123'. For multi-entity "
            "tasks, use these natural references to distinguish which entity each action "
            "applies to.\n"
            "- Use normal product/site language instead of schema language: say 'issue labeled bug' "
            "instead of 'labels is bug', 'page titled Privacy Policy' instead of "
            "'page_title_contains is Privacy Policy', and 'product named X' instead of "
            "'product_name is X'.\n"
            "- Avoid raw DSL words like perform, action, locator, add_label, close_issue, "
            "write_review, edit_page, or body_must_include.\n"
            "- Do not split strings into characters.\n"
            "- Return ONLY the final instruction text. No preamble, bullets, code fences, or JSON.\n\n"
            "Style guidance:\n"
            "- Prefer one compact paragraph with clear sequencing.\n"
            "- Start with the website/context, then identify target(s), then state the requested "
            "actions in order.\n"
            "- Make it sound like a practical user request, not a template."
        )
        user_msg = json.dumps(structured_task, ensure_ascii=False, indent=2)

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]
        return self._call_api(messages, temperature=self.temperature).strip()

    def judge_ambiguity(self, task_description: str, structured_task: dict) -> dict:
        """Check whether a task description is clear and consistent with its spec.

        Returns ``{"clear": bool, "issues": list[str]}``.
        """
        system_msg = (
            "You are a quality-assurance judge for browser automation task "
            "descriptions. You will receive a natural-language task description "
            "and the corresponding structured specification.\n\n"
            "Evaluate:\n"
            "1. Is the instruction clear and unambiguous?\n"
            "2. Does it match the structured specification?\n"
            "3. Are there missing or extra requirements compared to the spec?\n\n"
            "Respond with ONLY a JSON object (no code fences, no commentary):\n"
            '{"clear": true/false, "issues": ["issue 1", ...]}\n'
            'If the instruction is perfect, return {"clear": true, "issues": []}.'
        )
        user_msg = (
            f"Task description:\n{task_description}\n\n"
            f"Structured specification:\n"
            f"{json.dumps(structured_task, ensure_ascii=False, indent=2)}"
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]
        raw = self._call_api(messages, temperature=0.1).strip()

        # Strip code fences if the model wrapped its output
        if raw.startswith("```"):
            lines = raw.splitlines()
            # Remove first and last fence lines
            lines = [l for l in lines if not l.startswith("```")]
            raw = "\n".join(lines).strip()

        try:
            result = json.loads(raw)
            # Normalise to expected shape
            return {
                "clear": bool(result.get("clear", False)),
                "issues": list(result.get("issues", [])),
            }
        except (json.JSONDecodeError, TypeError, AttributeError):
            return {
                "clear": False,
                "issues": [
                    f"could not parse judge response: {raw[:200]}"
                ],
            }

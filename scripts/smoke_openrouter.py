"""Make one synthetic OpenRouter call and write inspectable local outputs."""

from __future__ import annotations

import asyncio
import os

from forge.application.budgets import DepthBudget, live_run_confirmation_prompt
from forge.application.decisions import ChoiceLetter, submit_decision
from forge.config import load_settings
from forge.domain.identifiers import new_call_id
from forge.domain.investigation import DepthMode
from forge.gateways.model import ModelMessage, ModelRequest, ModelRole
from forge.gateways.openrouter import OpenRouterGateway
from forge.observability.trace import TraceWriter, write_private_file
from forge.smoke_report import render_smoke_report


def confirm_live_smoke() -> bool:
    """Require a visible A-E approval for the one-call paid smoke boundary."""

    prompt = live_run_confirmation_prompt(
        investigation_id="inv_smoke_openrouter",
        depth=DepthMode.QUICK,
        budget=DepthBudget(max_calls=1, max_output_tokens_per_call=500),
        source_attached=False,
    )
    while True:
        print(prompt.question)
        for option in prompt.options:
            marker = " (recommended)" if option.is_recommended else ""
            print(f"  {option.letter.value}. {option.label}{marker}")
        raw = input("Choose A-E: ")
        custom = input("Custom answer: ") if raw.strip().upper() == ChoiceLetter.E else None
        attempt = submit_decision(prompt, raw, custom_answer=custom)
        if attempt.error is not None:
            print(attempt.error)
            continue
        assert attempt.selection is not None
        return attempt.selection.letter is ChoiceLetter.A


async def run() -> int:
    if not confirm_live_smoke():
        print("No provider call was made.")
        return 0
    settings = load_settings()
    investigation_id = "inv_smoke_openrouter"
    call_id = new_call_id()
    trace = TraceWriter(
        log_root=settings.log_dir,
        output_root=settings.output_dir,
        secret_values=(settings.openrouter_api_key.get_secret_value(),),
    )
    request = ModelRequest(
        investigation_id=investigation_id,
        call_id=call_id,
        role=ModelRole.LEAD,
        model=settings.model_lead,
        messages=(
            ModelMessage(
                role="system",
                content=(
                    "Reason from first principles only. Do not browse or appeal to authority. "
                    "Return a compact testable connection."
                ),
            ),
            ModelMessage(
                role="user",
                content=(
                    "Starting from conservation, constraint, and feedback, identify one useful "
                    "connection between two domains that is easy to overlook. State what remains "
                    "uncertain."
                ),
            ),
        ),
        output_schema={
            "type": "object",
            "properties": {
                "observation": {"type": "string"},
                "connection": {"type": "string"},
                "uncertainty": {"type": "string"},
            },
            "required": ["observation", "connection", "uncertainty"],
            "additionalProperties": False,
        },
        output_schema_name="first_principles_smoke",
        max_output_tokens=500,
        prompt_contract_version="smoke-v1",
    )
    async with OpenRouterGateway(
        api_key=settings.openrouter_api_key.get_secret_value(),
        base_url=str(settings.openrouter_base_url),
        trace=trace,
        timeout_seconds=60,
        max_retries=1,
    ) as gateway:
        result = await gateway.complete(request)

    report_path = settings.output_dir / "smoke" / "openrouter-smoke.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(settings.output_dir, 0o700)
    os.chmod(report_path.parent, 0o700)
    write_private_file(report_path, render_smoke_report(result))
    print(report_path)
    return 0 if result.is_success else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))

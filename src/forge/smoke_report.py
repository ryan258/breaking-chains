"""Human-readable report for a real model-gateway smoke call."""

from forge.gateways.model import ModelResult


def render_smoke_report(result: ModelResult) -> str:
    receipt = result.receipt
    lines = [
        "# OpenRouter Smoke Investigation",
        "",
        "## Run receipt",
        "",
        f"- Status: {'success' if result.is_success else 'failed'}",
        f"- Role: {receipt.role}",
        f"- Model: `{receipt.model}`",
        f"- Attempts: {receipt.attempts}",
        f"- Duration: {receipt.duration_ms} ms",
        f"- Tokens: {receipt.usage.total_tokens}",
        f"- Reported cost: {receipt.usage.cost}",
        f"- Full call artifact: `{receipt.artifact_path}`",
        "",
    ]
    if result.is_success and result.output is not None:
        lines.extend(
            [
                "## First-principles result",
                "",
                f"### Observation\n\n{result.output.get('observation', '')}",
                "",
                f"### Connection\n\n{result.output.get('connection', '')}",
                "",
                f"### Uncertainty\n\n{result.output.get('uncertainty', '')}",
            ]
        )
    else:
        lines.extend(
            [
                "## Failure",
                "",
                f"- Kind: {result.failure_kind}",
                f"- Message: {result.failure_message}",
            ]
        )
    return "\n".join(lines) + "\n"

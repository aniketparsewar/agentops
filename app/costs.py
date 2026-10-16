"""Token-price table. Estimates, not meter readings — update when prices change."""

# $ per 1M tokens: (input, output)
PRICES = {
    "gpt-4o-mini": (0.15, 0.60),
}


def estimate(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = PRICES[model]
    return input_tokens / 1e6 * price_in + output_tokens / 1e6 * price_out

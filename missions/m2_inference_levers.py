"""M2 — Inference Cost Levers: $/1M-token, batch x cache x cascade (deck §7).

Run: python missions/m2_inference_levers.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num
from finops import pricing, sustainability

# $/1M tokens (input, output) — illustrative 2026.
MODEL_PRICES = {"small": (0.20, 0.40), "large": (3.00, 15.00)}


def run(verbose: bool = True) -> dict:
    rows = load_csv("token_usage.csv")
    base_cost = opt_cost = 0.0
    total_tokens = 0

    # Extension 4 stats tracking
    reasoning_reqs = non_reasoning_reqs = 0
    reasoning_toks = non_reasoning_toks = 0
    reasoning_cost = non_reasoning_cost = 0.0
    reasoning_wh = non_reasoning_wh = 0.0

    # Calculate average cache reads for Extension 3 verification
    cached_rows = [r for r in rows if int(num(r["cached_input_tokens"])) > 0]
    avg_cache_reads = len(rows) / max(1, len(cached_rows))  # estimated reuse factor
    cache_economic = pricing.cache_is_worth_it(avg_reads=avg_cache_reads, write_cost_per_m=3.0, read_discount=0.10)

    for r in rows:
        inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
        cached = int(num(r["cached_input_tokens"])) if cache_economic else 0
        is_batch = bool(int(num(r["is_batch"])))
        is_reasoning = bool(int(num(r.get("is_reasoning", 0))))
        req_toks = inp + out
        total_tokens += req_toks

        # BASELINE: naive deployment — everything on the large model, no cache, no batch
        lin, lout = MODEL_PRICES["large"]
        base_cost += pricing.request_cost(inp, out, lin, lout)

        # OPTIMIZED: cascade (route_tier), prompt caching, batch API
        pin, pout = MODEL_PRICES[r["route_tier"]]
        cost = pricing.request_cost(inp, out, pin, pout, cached_in=cached, batch=is_batch)
        opt_cost += cost

        req_wh = sustainability.wh_per_query(req_toks, is_reasoning=is_reasoning)

        if is_reasoning:
            reasoning_reqs += 1
            reasoning_toks += req_toks
            reasoning_cost += cost
            reasoning_wh += req_wh
        else:
            non_reasoning_reqs += 1
            non_reasoning_toks += req_toks
            non_reasoning_cost += cost
            non_reasoning_wh += req_wh

    base_pm = pricing.dollars_per_million(base_cost, total_tokens)
    opt_pm = pricing.dollars_per_million(opt_cost, total_tokens)
    savings_pct = (1 - opt_cost / base_cost) * 100 if base_cost else 0.0

    reasoning_req_pct = (reasoning_reqs / len(rows) * 100) if rows else 0.0
    reasoning_cost_pct = (reasoning_cost / opt_cost * 100) if opt_cost > 0 else 0.0
    reasoning_wh_pct = (reasoning_wh / (reasoning_wh + non_reasoning_wh) * 100) if (reasoning_wh + non_reasoning_wh) > 0 else 0.0

    if verbose:
        print("== M2 Inference Cost Levers ==")
        print(f"requests={len(rows)}  tokens={total_tokens:,}")
        print(f"baseline  : ${base_cost:,.2f}/day   ${base_pm:.3f}/1M-token")
        print(f"optimized : ${opt_cost:,.2f}/day   ${opt_pm:.3f}/1M-token")
        print(f"savings   : {savings_pct:.1f}%  (cascade + caching + batch)")
        print(f"discount stack (batch + 100% cache): {pricing.discount_stack(batch=True, cache_hit_frac=1.0):.3f} of naive")

        print("\n--- Extension 3: Prompt Caching Economics ---")
        print(f"Avg cache reuse factor: {avg_cache_reads:.2f} reads | Minimum required: {pricing.break_even_cache_reads():.2f} reads")
        print(f"Prompt caching active: {cache_economic} (Economic benefit verified)")

        print("\n--- Extension 4: Reasoning Traffic Budget Analysis ---")
        print(f"Reasoning requests: {reasoning_reqs} ({reasoning_req_pct:.1f}% of total traffic)")
        print(f"Reasoning cost: ${reasoning_cost:,.2f}/day ({reasoning_cost_pct:.1f}% of optimized spend)")
        print(f"Reasoning energy: {reasoning_wh:,.1f} Wh/day ({reasoning_wh_pct:.1f}% of total energy consumption)")

    return {
        "baseline_daily": round(base_cost, 2), "optimized_daily": round(opt_cost, 2),
        "baseline_per_m": round(base_pm, 3), "optimized_per_m": round(opt_pm, 3),
        "savings_pct": round(savings_pct, 1), "total_tokens": total_tokens,
        "cache_economic": cache_economic,
        "reasoning_stats": {
            "reqs": reasoning_reqs,
            "req_pct": round(reasoning_req_pct, 1),
            "cost_daily": round(reasoning_cost, 2),
            "cost_pct": round(reasoning_cost_pct, 1),
            "energy_wh_daily": round(reasoning_wh, 1),
            "energy_pct": round(reasoning_wh_pct, 1),
        }
    }


if __name__ == "__main__":
    run()


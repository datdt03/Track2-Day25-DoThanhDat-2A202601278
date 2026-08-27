"""Pricing & purchasing economics — measure in $/1M-token, not $/GPU-hr.

Figures are June-2026 as-of snapshots from the deck's RESEARCH dossier; treat
live prices as fast-moving (re-baseline before each cohort).
"""
from __future__ import annotations


def request_cost(
    input_tok: int,
    output_tok: int,
    price_in_per_m: float,
    price_out_per_m: float,
    cached_in: int = 0,
    cache_discount: float = 0.10,   # Anthropic cached-read ~0.1x (=-90%)
    batch: bool = False,
    batch_discount: float = 0.50,   # Batch API ~ -50%
) -> float:
    """USD cost of a single request. Cached input billed at cache_discount x price."""
    cached_in = min(max(0, cached_in), input_tok)
    uncached_in = input_tok - cached_in
    cost = (
        (uncached_in / 1e6) * price_in_per_m
        + (cached_in / 1e6) * price_in_per_m * cache_discount
        + (output_tok / 1e6) * price_out_per_m
    )
    if batch:
        cost *= batch_discount
    return cost


def dollars_per_million(total_cost_usd: float, total_tokens: int) -> float:
    """Aggregate unit economics: $ per 1,000,000 tokens served."""
    if total_tokens <= 0:
        return 0.0
    return total_cost_usd / (total_tokens / 1e6)


def discount_stack(
    batch: bool = False,
    cache_hit_frac: float = 0.0,
    batch_discount: float = 0.50,
    cache_discount: float = 0.10,
) -> float:
    """Effective fraction of the naive bill after stacking discounts (input-heavy view).

    Discounts MULTIPLY: cache applies to the cached share of input, batch to the
    whole bill. batch + 100% cache-hit -> 0.5 * 0.1 = 0.05 (~95% off).
    """
    cache_mult = cache_hit_frac * cache_discount + (1.0 - cache_hit_frac)
    batch_mult = batch_discount if batch else 1.0
    return cache_mult * batch_mult


def break_even_utilization(discount_frac: float) -> float:
    """Utilization at which a commitment pays off ~= 1 - discount.

    A 45% reserved discount needs ~55% utilization (~13.2h/day) to beat on-demand.
    """
    return max(0.0, min(1.0, 1.0 - discount_frac))


    return max(0.0, min(1.0, 1.0 - discount_frac))


def cache_is_worth_it(
    avg_reads: float,
    write_cost_per_m: float = 3.0,
    read_discount: float = 0.10,
    write_surcharge: float = 1.0,
) -> bool:
    """Extension 3: Determines if prompt caching is economically beneficial based on avg reads.

    Break-even equation:
    Without cache: N_reads * P_in
    With cache: (P_in * write_surcharge) + (N_reads - 1) * P_in * read_discount

    Setting equality gives: N_min = (write_surcharge - read_discount) / (1.0 - read_discount).
    Returns True if avg_reads >= break_even_reads.
    """
    if 1.0 - read_discount <= 0:
        return False
    break_even_reads = (write_surcharge - read_discount) / (1.0 - read_discount)
    return avg_reads >= break_even_reads


def break_even_cache_reads(read_discount: float = 0.10, write_surcharge: float = 1.0) -> float:
    """Return the minimum average reads required to break even on prompt caching."""
    if 1.0 - read_discount <= 0:
        return float("inf")
    return (write_surcharge - read_discount) / (1.0 - read_discount)


def recommend_tier(
    hours_per_day: float,
    interruptible: bool,
    reserved_discount: float = 0.45,
    interruption_rate: float = 0.05,
    res_1yr_discount: float = 0.30,
    res_3yr_discount: float = 0.45,
    max_term_years: int = 3,
    policy: str = "standard",
) -> str:
    """Pick a purchasing tier from a workload's duty cycle + interruptibility.

    DOCUMENTED simple policy (standard):
      - interruptible & not 24/7  -> 'spot'      (checkpoint and ride the discount)
      - duty cycle >= break-even  -> 'reserved'  (steady, high utilization)
      - otherwise                 -> 'on_demand' (spiky / low duty)

    ADVANCED policy (Extension 1):
      - Accounts for interruption rate risk on spot and compares 1yr vs 3yr commitment risk.
      - Returns 'spot', 'reserved_3yr', 'reserved_1yr', or 'on_demand'.
    """
    duty = max(0.0, hours_per_day) / 24.0
    be_3yr = break_even_utilization(res_3yr_discount)
    be_1yr = break_even_utilization(res_1yr_discount)

    if policy == "advanced":
        if interruptible and hours_per_day < 24 and interruption_rate < 0.15:
            return "spot"
        if max_term_years >= 3 and duty >= be_3yr:
            return "reserved_3yr"
        elif max_term_years >= 1 and duty >= be_1yr:
            return "reserved_1yr"
        return "on_demand"

    if interruptible and hours_per_day < 24:
        return "spot"
    if duty >= be_3yr:
        return "reserved"
    return "on_demand"



def spot_checkpoint_cost(
    job_hours: float,
    spot_hr: float,
    on_demand_hr: float,
    interrupt_rate: float = 0.05,      # per-hour chance (H100 spot ~<5%)
    ckpt_overhead_frac: float = 0.03,  # steady cost of writing checkpoints
    rework_hours_per_interrupt: float = 0.5,
) -> dict:
    """Effective cost of running a checkpointable job on spot vs on-demand.

    Interruptions waste the compute since the last checkpoint (rework); checkpointing
    adds a small steady overhead. Spot still wins for interruptible jobs.
    """
    expected_interrupts = job_hours * interrupt_rate
    rework_hours = expected_interrupts * rework_hours_per_interrupt
    effective_hours = job_hours * (1.0 + ckpt_overhead_frac) + rework_hours
    spot_cost = effective_hours * spot_hr
    on_demand_cost = job_hours * on_demand_hr
    savings_pct = (1.0 - spot_cost / on_demand_cost) * 100.0 if on_demand_cost > 0 else 0.0
    return {
        "spot_effective_hours": round(effective_hours, 2),
        "spot_cost": round(spot_cost, 2),
        "on_demand_cost": round(on_demand_cost, 2),
        "savings_pct": round(savings_pct, 1),
    }


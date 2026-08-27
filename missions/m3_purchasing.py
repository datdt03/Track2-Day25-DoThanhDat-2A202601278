"""M3 — Purchasing Strategy: break-even, tier choice, spot-checkpoint sim (deck §4).

Run: python missions/m3_purchasing.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num, catalog_by_type
from finops import pricing, sustainability

DAYS = 30


def run(verbose: bool = True) -> dict:
    jobs = load_csv("workloads.csv")
    cat = catalog_by_type()
    on_demand_monthly = optimized_monthly = 0.0
    recs = []
    interruptible_gpu_kwh = 0.0

    for j in jobs:
        gtype = j["gpu_type"]
        ngpu = int(num(j["num_gpus"]))
        hpd = num(j["hours_per_day"])
        interruptible = bool(int(num(j["interruptible"])))
        c = cat[gtype]
        gpu_hours = hpd * DAYS * ngpu
        od = num(c["on_demand_hr"])
        on_demand_cost = gpu_hours * od

        tier = pricing.recommend_tier(hpd, interruptible)
        if tier == "spot":
            sim = pricing.spot_checkpoint_cost(gpu_hours, num(c["spot_hr"]), od)
            opt_cost = sim["spot_cost"]
        elif tier == "reserved":
            opt_cost = gpu_hours * num(c["reserved_3yr_hr"])
        else:
            opt_cost = on_demand_cost

        if interruptible:
            watts = num(c.get("watts", 500))
            interruptible_gpu_kwh += (gpu_hours * watts) / 1000.0

        on_demand_monthly += on_demand_cost
        optimized_monthly += opt_cost
        recs.append({"job_id": j["job_id"], "gpu_type": gtype, "tier": tier,
                     "on_demand": round(on_demand_cost), "optimized": round(opt_cost)})

    savings = on_demand_monthly - optimized_monthly
    savings_pct = savings / on_demand_monthly * 100 if on_demand_monthly else 0.0

    # --- Extension 5: Carbon-aware Regional Analysis ---
    region_comparison = {}
    default_region_carbon = sustainability.carbon_g(interruptible_gpu_kwh * 1000.0, "us-east-1") / 1000.0 # kgCO2e
    for reg, gco2_kwh in sustainability.REGION_CARBON.items():
        car_kg = (interruptible_gpu_kwh * gco2_kwh) / 1000.0
        elec_usd = interruptible_gpu_kwh * sustainability.REGION_PRICE_KWH[reg]
        region_comparison[reg] = {
            "carbon_intensity_g_kwh": gco2_kwh,
            "elec_price_per_kwh": sustainability.REGION_PRICE_KWH[reg],
            "total_carbon_kg": round(car_kg, 1),
            "total_elec_usd": round(elec_usd, 2)
        }

    cleanest_region = min(region_comparison, key=lambda r: region_comparison[r]["total_carbon_kg"])
    cleanest_carbon_kg = region_comparison[cleanest_region]["total_carbon_kg"]
    carbon_saved_kg = default_region_carbon - cleanest_carbon_kg
    carbon_saved_pct = (carbon_saved_kg / default_region_carbon * 100) if default_region_carbon > 0 else 0.0

    if verbose:
        print("== M3 Purchasing Strategy ==")
        print(f"break-even utilization @ 45% reserved discount = {pricing.break_even_utilization(0.45):.0%}")
        print(f"{'job':18}{'gpu':7}{'tier':11}{'on-demand':>12}{'optimized':>12}")
        for r in recs:
            print(f"{r['job_id']:18}{r['gpu_type']:7}{r['tier']:11}${r['on_demand']:>11,}${r['optimized']:>11,}")
        print(f"\nmonthly: on-demand ${on_demand_monthly:,.0f} -> optimized ${optimized_monthly:,.0f}  ({savings_pct:.1f}% saved)")

        print("\n--- Extension 5: Carbon-Aware Regional Scheduling Analysis ---")
        print(f"Interruptible training workload energy: {interruptible_gpu_kwh:,.0f} kWh/month")
        print(f"{'Region':18}{'gCO2/kWh':>12}{'$/kWh':>10}{'Monthly Carbon (kg)':>20}{'Electricity Cost':>18}")
        for reg, stats in region_comparison.items():
            print(f"{reg:18}{stats['carbon_intensity_g_kwh']:>12}{stats['elec_price_per_kwh']:>10.3f}${stats['total_carbon_kg']:>19,.1f} kg${stats['total_elec_usd']:>17,.2f}")
        print(f"Carbon Reduction by scheduling in '{cleanest_region}': {carbon_saved_kg:,.1f} kg CO2e saved ({carbon_saved_pct:.1f}% reduction vs us-east-1)")

    return {
        "recommendations": recs, "on_demand_monthly": round(on_demand_monthly),
        "optimized_monthly": round(optimized_monthly), "savings_pct": round(savings_pct, 1),
        "region_comparison": region_comparison,
        "cleanest_region": cleanest_region,
        "carbon_saved_kg": round(carbon_saved_kg, 1),
    }


if __name__ == "__main__":
    run()


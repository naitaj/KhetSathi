"""CLI runner for KhetSathi simulation counterfactual."""

import argparse
import json
import sys
from pathlib import Path

# Ensure paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "simulation"))
sys.path.insert(0, str(PROJECT_ROOT / "decision-engine"))

from simulator import IrrigationSimulator


def main():
    parser = argparse.ArgumentParser(description="Run KhetSathi vs Baseline Irrigation Simulation")
    parser.add_argument(
        "--scenario",
        type=str,
        default=str(PROJECT_ROOT / "data" / "scenarios" / "bihar_maize_season.json"),
        help="Path to scenario JSON file",
    )
    parser.add_argument("--interval", type=int, default=4, help="Baseline irrigation interval (days)")
    parser.add_argument("--duration", type=int, default=45, help="Baseline irrigation duration (min)")
    parser.add_argument("--output", type=str, default="", help="Optional output JSON path")
    parser.add_argument("--verify", action="store_true", help="Run reproducibility verification test")

    args = parser.parse_args()

    scenario_file = Path(args.scenario)
    if not scenario_file.exists():
        print(f"Error: Scenario file not found at {scenario_file}", file=sys.stderr)
        sys.exit(1)

    sim = IrrigationSimulator.from_scenario_file(scenario_file)
    results = sim.run(baseline_interval_days=args.interval, baseline_duration_minutes=args.duration)

    summary = results["summary"]
    base = summary["baseline"]
    khet = summary["khetsathi"]
    impact = summary["impact"]

    print("\n" + "=" * 65)
    print("      KHETSATHI IRRIGATION SIMULATION RESULTS [SIMULATED]")
    print("=" * 65)
    print(f"Scenario:    {results['scenario_id']} ({results['location']})")
    print(f"Crop / Area: {results['crop'].title()} | {results['area_ha']} ha | {results['simulated_days']} Days Replay")
    print("-" * 65)
    print(f"{'Metric':<30} | {'Baseline (Fixed)':<15} | {'KhetSathi':<15}")
    print("-" * 65)
    print(f"{'Irrigation Events':<30} | {base['irrigation_events']:<15} | {khet['irrigation_events']:<15}")
    print(f"{'Pump Hours':<30} | {base['pump_hours']:<15} | {khet['pump_hours']:<15}")
    print(f"{'Water Applied (Litres)':<30} | {base['water_applied_liters']:<15,.0f} | {khet['water_applied_liters']:<15,.0f}")
    print(f"{'Pump Energy (kWh)':<30} | {base['pump_energy_kwh']:<15.1f} | {khet['pump_energy_kwh']:<15.1f}")
    print(f"{'Crop Stress Days':<30} | {base['crop_stress_days']:<15} | {khet['crop_stress_days']:<15}")
    print("-" * 65)
    print("ENVIRONMENTAL IMPACT [SIMULATED]:")
    print(f"  • Water Saved:             {impact['water_saved_liters']:,.0f} Litres ({impact['water_saved_percent']}%)")
    print(f"  • Avoided Pump Hours:      {impact['avoided_pump_hours']:.1f} hours")
    print(f"  • Avoided Pumping Energy:  {impact['avoided_energy_kwh']:.2f} kWh")
    print(f"  • Avoided Events:          {impact['avoided_irrigation_events']} events")
    print(f"  • Stress Days Delta:       {impact['crop_stress_days_difference']} days")
    print("=" * 65)
    print(f"NOTE: {results['disclaimer']}\n")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {out_path}")

    if args.verify:
        print("Running reproducibility verification check...")
        sim2 = IrrigationSimulator.from_scenario_file(scenario_file)
        results2 = sim2.run(baseline_interval_days=args.interval, baseline_duration_minutes=args.duration)
        if json.dumps(results["summary"]) == json.dumps(results2["summary"]):
            print("REPRODUCIBILITY VERIFIED: Bit-for-bit identical results on consecutive runs.")
        else:
            print("VERIFICATION FAILED: Simulation output nondeterministic!", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

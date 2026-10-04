"""
sortie_model.py — Logistics/sortie-rate model for a heavy-lift drone shuttle.

Answers: given a route distance and a daily tonnage requirement, how many
aircraft do I need, and what does the energy logistics chain look like?

Mission profile per sortie (loaded out, empty back):
  climb -> loaded cruise -> hover/place payload -> empty cruise back
  -> land -> battery swap or refuel -> repeat

Run:  python3 sortie_model.py
Edit CONFIG and re-run. Pairs with sizing.py (uses its hover power model).
"""

import math

# ----------------------------- CONFIG -----------------------------------
# Vehicle (defaults match sizing.py output)
EMPTY_MASS_KG    = 4.5
ENERGY_MASS_KG   = 1.5
PAYLOAD_KG       = 18.0
DISK_AREA_M2     = 3.17      # 8 x 28" props
FIGURE_OF_MERIT  = 0.70
ETA_ELEC         = 0.85
RHO, G           = 1.225, 9.81

# Route & ops
ROUTE_KM          = 2.0      # one-way distance
CRUISE_MPS        = 15.0     # ~34 mph
HOVER_TIME_S      = 90.0     # pickup + placement hover per sortie
CLIMB_ENERGY_FUDGE = 1.10    # +10% for climbs/accels
RESERVE_FRAC      = 0.20     # never plan below 20% energy reserve
CRUISE_POWER_FRAC = 0.80     # forward flight power ~80% of hover (translational lift)

# Ground ops
SWAP_TIME_MIN     = 2.0      # automated battery swap / hot refuel
LOAD_TIME_MIN     = 2.0      # hook/release cargo
OPS_HOURS_PER_DAY = 10.0
AVAILABILITY      = 0.80     # 20% of fleet in maintenance at any time

# Requirement
DAILY_TONNES      = 5.0      # cargo to move per day

# Energy system
BATT_WH_PER_KG    = 250.0
BATT_USABLE_FRAC  = 0.80
GRID_COST_PER_KWH = 0.15     # USD, for cost-per-ton-km estimate
# -------------------------------------------------------------------------


def hover_power_w(mass_kg: float) -> float:
    t = mass_kg * G
    p = t ** 1.5 / math.sqrt(2 * RHO * DISK_AREA_M2)
    return p / (FIGURE_OF_MERIT * ETA_ELEC)


def main() -> None:
    m_loaded = EMPTY_MASS_KG + ENERGY_MASS_KG + PAYLOAD_KG
    m_empty  = EMPTY_MASS_KG + ENERGY_MASS_KG

    p_hover_loaded = hover_power_w(m_loaded)
    p_hover_empty  = hover_power_w(m_empty)
    p_cruise_loaded = p_hover_loaded * CRUISE_POWER_FRAC
    p_cruise_empty  = p_hover_empty * CRUISE_POWER_FRAC

    t_leg_s = ROUTE_KM * 1000 / CRUISE_MPS

    # Energy per round trip (Wh)
    e_out   = p_cruise_loaded * t_leg_s / 3600
    e_hover = p_hover_loaded * HOVER_TIME_S / 3600
    e_back  = p_cruise_empty * t_leg_s / 3600
    e_trip  = (e_out + e_hover + e_back) * CLIMB_ENERGY_FUDGE

    batt_usable = ENERGY_MASS_KG * BATT_WH_PER_KG * BATT_USABLE_FRAC
    batt_plannable = batt_usable * (1 - RESERVE_FRAC)
    trips_per_charge = batt_plannable / e_trip

    # Cycle time per sortie (minutes)
    t_air_min = (2 * t_leg_s + HOVER_TIME_S) / 60
    swaps_per_trip = 1 / trips_per_charge if trips_per_charge < 1 else \
        (1 / math.floor(trips_per_charge) if trips_per_charge >= 1 else 1)
    # simpler: amortize swap time across trips per charge
    swap_amortized = SWAP_TIME_MIN / max(trips_per_charge, 1e-9) \
        if trips_per_charge < 1 else SWAP_TIME_MIN / math.floor(max(trips_per_charge, 1))
    t_cycle_min = t_air_min + LOAD_TIME_MIN + swap_amortized

    sorties_per_ac_day = OPS_HOURS_PER_DAY * 60 / t_cycle_min
    tonnes_per_ac_day  = sorties_per_ac_day * PAYLOAD_KG / 1000

    fleet_flying = DAILY_TONNES / tonnes_per_ac_day
    fleet_total  = math.ceil(fleet_flying / AVAILABILITY)

    sorties_day_total = DAILY_TONNES * 1000 / PAYLOAD_KG
    kwh_day = sorties_day_total * e_trip / 1000
    ton_km_day = DAILY_TONNES * ROUTE_KM
    cost_per_ton_km = kwh_day * GRID_COST_PER_KWH / ton_km_day

    print("=" * 62)
    print(" SORTIE-RATE / FLEET MODEL — heavy-lift shuttle")
    print("=" * 62)
    print(f" Route (one-way)        : {ROUTE_KM:5.1f} km @ {CRUISE_MPS*3.6:.0f} km/h")
    print(f" Payload per sortie     : {PAYLOAD_KG:5.1f} kg")
    print(f" Requirement            : {DAILY_TONNES:5.1f} tonnes/day "
          f"({sorties_day_total:.0f} sorties)")
    print("-" * 62)
    print(f" Energy per round trip  : {e_trip:6.1f} Wh "
          f"(out {e_out:.0f} + hover {e_hover:.0f} + back {e_back:.0f}, +10%)")
    print(f" Usable battery (plan)  : {batt_plannable:6.1f} Wh "
          f"({RESERVE_FRAC*100:.0f}% reserve held)")
    print(f" Trips per charge       : {trips_per_charge:6.2f}")
    print("-" * 62)
    print(f" Airborne time / sortie : {t_air_min:5.1f} min")
    print(f" Full cycle / sortie    : {t_cycle_min:5.1f} min "
          f"(load {LOAD_TIME_MIN:.0f} + swap amort. {swap_amortized:.1f})")
    print(f" Sorties per a/c per day: {sorties_per_ac_day:5.1f}")
    print(f" Tonnage per a/c per day: {tonnes_per_ac_day:5.2f} t")
    print("-" * 62)
    print(f" Aircraft flying needed : {fleet_flying:5.1f}")
    print(f" FLEET SIZE @ {AVAILABILITY*100:.0f}% avail: {fleet_total:d} aircraft")
    print(f" Daily energy           : {kwh_day:6.1f} kWh "
          f"(~${kwh_day*GRID_COST_PER_KWH:,.2f} grid cost)")
    print(f" Energy cost / ton-km   : ${cost_per_ton_km:6.3f}")
    print("=" * 62)
    print(" Levers to pull: route distance, swap time, ops hours,")
    print(" payload, cruise speed. Change CONFIG and re-run.")


if __name__ == "__main__":
    main()

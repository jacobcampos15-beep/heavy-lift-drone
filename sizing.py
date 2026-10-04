"""
sizing.py — First-pass physics sizing for a 4:1 heavy-lift multirotor.

Momentum theory (actuator disk) hover model with a figure-of-merit
correction, plus energy sizing for battery-electric vs hybrid power.

Run:  python3 sizing.py
Edit the CONFIG block and re-run to explore the design space.

Author notes:
- Units are SI internally; printed output shows both SI and imperial.
- Figure of merit (FM) ~0.60-0.75 for well-designed props. 0.70 default.
- T/W margin: hover uses thrust = weight; max throttle should give
  ~1.4-1.6x hover thrust for control authority. We size motors for that.
"""

import math

# ----------------------------- CONFIG -----------------------------------
EMPTY_MASS_KG   = 4.5      # vehicle empty mass (structure+motors+avionics)
PAYLOAD_RATIO   = 4.0      # payload = ratio * empty mass
ENERGY_MASS_KG  = 1.5      # battery OR (fuel+genset) mass, counted separately
N_ROTORS        = 8        # coaxial octo = 8 props
ROTOR_DIAM_M    = 0.71     # 28-inch props
FIGURE_OF_MERIT = 0.70     # rotor efficiency vs ideal actuator disk
ETA_ELEC        = 0.85     # motor+ESC electrical efficiency
RHO             = 1.225    # air density, kg/m^3 (sea level, 15C)
G               = 9.81

CONTROL_MARGIN  = 1.5      # max thrust / hover thrust for maneuvering

# Energy options
BATT_WH_PER_KG   = 250.0   # Li-ion pack, realistic installed
BATT_USABLE_FRAC = 0.80    # don't run packs to zero
FUEL_WH_PER_KG   = 12000.0 # Jet-A specific energy
GENSET_ETA       = 0.25    # small turbogenerator fuel->electric efficiency
GENSET_MASS_FRAC = 0.55    # fraction of ENERGY_MASS that is genset hardware
# -------------------------------------------------------------------------


def hover_power_w(thrust_n: float, disk_area_m2: float) -> float:
    """Ideal hover power corrected by figure of merit and electrical eff."""
    p_ideal = thrust_n ** 1.5 / math.sqrt(2.0 * RHO * disk_area_m2)
    return p_ideal / (FIGURE_OF_MERIT * ETA_ELEC)


def main() -> None:
    payload_kg = PAYLOAD_RATIO * EMPTY_MASS_KG
    gross_kg   = EMPTY_MASS_KG + ENERGY_MASS_KG + payload_kg
    hover_T_n  = gross_kg * G

    disk_area = N_ROTORS * math.pi * (ROTOR_DIAM_M / 2) ** 2
    disk_loading = hover_T_n / disk_area  # N/m^2

    p_hover = hover_power_w(hover_T_n, disk_area)
    p_max_thrust = hover_T_n * CONTROL_MARGIN
    p_max = hover_power_w(p_max_thrust, disk_area)

    per_motor_hover_w = p_hover / N_ROTORS
    per_motor_max_w   = p_max / N_ROTORS
    per_motor_max_T   = p_max_thrust / N_ROTORS

    # ---- Endurance: battery-electric -------------------------------------
    batt_wh = ENERGY_MASS_KG * BATT_WH_PER_KG * BATT_USABLE_FRAC
    t_batt_min = batt_wh / p_hover * 60.0

    # ---- Endurance: hybrid (genset + small buffer battery) ---------------
    fuel_kg = ENERGY_MASS_KG * (1.0 - GENSET_MASS_FRAC)
    hyb_wh  = fuel_kg * FUEL_WH_PER_KG * GENSET_ETA
    t_hyb_min = hyb_wh / p_hover * 60.0

    lb = 2.20462
    print("=" * 62)
    print(" 4:1 HEAVY-LIFT SIZING — momentum theory first pass")
    print("=" * 62)
    print(f" Empty mass          : {EMPTY_MASS_KG:6.1f} kg  ({EMPTY_MASS_KG*lb:5.1f} lb)")
    print(f" Energy system mass  : {ENERGY_MASS_KG:6.1f} kg  ({ENERGY_MASS_KG*lb:5.1f} lb)")
    print(f" Payload ({PAYLOAD_RATIO:.0f}:1)       : {payload_kg:6.1f} kg  ({payload_kg*lb:5.1f} lb)")
    print(f" Gross takeoff mass  : {gross_kg:6.1f} kg  ({gross_kg*lb:5.1f} lb)")
    print("-" * 62)
    print(f" Rotors              : {N_ROTORS} x {ROTOR_DIAM_M*39.37:.0f}-inch")
    print(f" Total disk area     : {disk_area:6.2f} m^2")
    print(f" Disk loading        : {disk_loading:6.1f} N/m^2 "
          f"({disk_loading/G:4.1f} kg/m^2)")
    print("-" * 62)
    print(f" Hover power (elec)  : {p_hover/1000:6.2f} kW")
    print(f" Max power (T/W {CONTROL_MARGIN:.1f}) : {p_max/1000:6.2f} kW")
    print(f" Per motor, hover    : {per_motor_hover_w:6.0f} W")
    print(f" Per motor, max      : {per_motor_max_w:6.0f} W   "
          f"(thrust {per_motor_max_T/G:4.1f} kgf)")
    print("-" * 62)
    print(f" Battery endurance   : {t_batt_min:6.1f} min hover "
          f"({batt_wh:.0f} Wh usable)")
    print(f" Hybrid endurance    : {t_hyb_min:6.1f} min hover "
          f"({hyb_wh:.0f} Wh from {fuel_kg:.2f} kg fuel)")
    print("=" * 62)
    print(" Sanity checks:")
    print(f"  - Disk loading under ~250 N/m^2 keeps downwash/noise sane: "
          f"{'OK' if disk_loading < 250 else 'HIGH'}")
    print(f"  - Per-motor max under ~4 kW is COTS territory: "
          f"{'OK' if per_motor_max_w < 4000 else 'CUSTOM MOTORS NEEDED'}")


if __name__ == "__main__":
    main()

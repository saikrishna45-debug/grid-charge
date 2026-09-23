from dataclasses import dataclass
from typing import List, Dict


# ============================================================
# SMART EV CHARGING OPTIMIZER - VERSION 6
# ============================================================
#
# V6 improvements:
#
# 1. Deadline feasibility analysis
# 2. Look-ahead charging requirement
# 3. Critical EV detection
# 4. Deadline slack calculation
# 5. Fairness / anti-starvation
# 6. Solar-aware charging
# 7. Grid safety enforcement
# 8. Maximum achievable SOC calculation
# 9. Explainable charging decisions
# 10. Multiple simulation scenarios
#
# Architecture:
#
# Current EV State
#       ↓
# Energy Requirement
#       ↓
# Remaining Time
#       ↓
# Deadline Feasibility
#       ↓
# Required Charging Power
#       ↓
# Deadline Slack
#       ↓
# Smart Allocation
#       ↓
# Grid Safety Check
#       ↓
# SOC Update
#
# ============================================================


# ============================================================
# EV DATA MODEL
# ============================================================

@dataclass
class EV:

    ev_id: str

    battery_capacity_kwh: float

    current_soc: float

    target_soc: float

    arrival_minute: int

    departure_minute: int

    max_charging_power_kw: float

    # Runtime values
    charging_power_kw: float = 0.0

    charging_reason: str = "Not charging"


# ============================================================
# BASIC ENERGY CALCULATIONS
# ============================================================

def calculate_energy_required(ev: EV) -> float:
    """
    Energy still required to reach target SOC.
    """

    if ev.current_soc >= ev.target_soc:
        return 0.0

    energy_required = (
        ev.battery_capacity_kwh
        * (ev.target_soc - ev.current_soc)
        / 100
    )

    return max(0.0, energy_required)


# ============================================================
# TIME CALCULATIONS
# ============================================================

def calculate_time_remaining(
    ev: EV,
    current_minute: int
) -> float:
    """
    Remaining minutes until EV departure.
    """

    return max(
        0,
        ev.departure_minute - current_minute
    )


# ============================================================
# REQUIRED POWER
# ============================================================

def calculate_required_power(
    ev: EV,
    current_minute: int
) -> float:
    """
    Average power required to reach target SOC
    before departure.
    """

    energy_required = calculate_energy_required(ev)

    if energy_required <= 0:
        return 0.0

    time_remaining = calculate_time_remaining(
        ev,
        current_minute
    )

    if time_remaining <= 0:
        return float("inf")

    hours_remaining = time_remaining / 60

    return energy_required / hours_remaining


# ============================================================
# MAXIMUM POSSIBLE ENERGY
# ============================================================

def calculate_max_possible_energy(
    ev: EV,
    current_minute: int
) -> float:
    """
    Maximum energy the EV can receive before departure,
    assuming its charger operates continuously at maximum power.
    """

    time_remaining = calculate_time_remaining(
        ev,
        current_minute
    )

    if time_remaining <= 0:
        return 0.0

    hours_remaining = time_remaining / 60

    return (
        ev.max_charging_power_kw
        * hours_remaining
    )


# ============================================================
# MAXIMUM ACHIEVABLE SOC
# ============================================================

def calculate_max_achievable_soc(
    ev: EV,
    current_minute: int
) -> float:
    """
    Calculate the highest SOC physically achievable
    before departure.
    """

    max_energy = calculate_max_possible_energy(
        ev,
        current_minute
    )

    max_soc_increase = (
        max_energy
        / ev.battery_capacity_kwh
        * 100
    )

    maximum_soc = (
        ev.current_soc
        + max_soc_increase
    )

    return min(
        100.0,
        maximum_soc
    )


# ============================================================
# DEADLINE FEASIBILITY
# ============================================================

def check_completion_feasibility(
    ev: EV,
    current_minute: int
) -> bool:
    """
    Determine whether target SOC can still be reached
    before departure using the maximum charger power.
    """

    energy_required = calculate_energy_required(ev)

    max_possible_energy = calculate_max_possible_energy(
        ev,
        current_minute
    )

    return (
        energy_required
        <= max_possible_energy + 1e-6
    )


# ============================================================
# FEASIBILITY RATIO
# ============================================================

def calculate_feasibility_ratio(
    ev: EV,
    current_minute: int
) -> float:
    """
    Ratio:

        Required Energy
        ----------------
        Maximum Possible Energy

    Interpretation:

    < 0.50  -> comfortable
    0.50-0.80 -> moderate pressure
    0.80-1.00 -> critical
    > 1.00 -> impossible
    """

    energy_required = calculate_energy_required(ev)

    if energy_required <= 0:
        return 0.0

    maximum_possible = calculate_max_possible_energy(
        ev,
        current_minute
    )

    if maximum_possible <= 0:
        return float("inf")

    return (
        energy_required
        / maximum_possible
    )


# ============================================================
# DEADLINE SLACK
# ============================================================

def calculate_deadline_slack(
    ev: EV,
    current_minute: int
) -> float:
    """
    Slack = maximum possible energy - required energy.

    Positive:
        There is enough theoretical capacity.

    Zero:
        EV is exactly at the feasibility boundary.

    Negative:
        EV cannot reach target anymore.
    """

    required_energy = calculate_energy_required(ev)

    maximum_energy = calculate_max_possible_energy(
        ev,
        current_minute
    )

    return maximum_energy - required_energy


# ============================================================
# BATTERY URGENCY
# ============================================================

def calculate_battery_urgency(ev: EV) -> float:
    """
    Lower SOC means greater urgency.
    """

    urgency = (
        100 - ev.current_soc
    ) / 100

    return max(
        0.0,
        min(1.0, urgency)
    )


# ============================================================
# DEPARTURE URGENCY
# ============================================================

def calculate_departure_urgency(
    ev: EV,
    current_minute: int
) -> float:
    """
    Less time remaining means higher urgency.
    """

    time_remaining = calculate_time_remaining(
        ev,
        current_minute
    )

    # Four-hour reference window
    urgency = (
        1
        - time_remaining / 240
    )

    return max(
        0.0,
        min(1.0, urgency)
    )


# ============================================================
# ENERGY URGENCY
# ============================================================

def calculate_energy_urgency(ev: EV) -> float:
    """
    More remaining energy means higher urgency.
    """

    energy_required = calculate_energy_required(ev)

    # 60 kWh reference
    urgency = energy_required / 60

    return max(
        0.0,
        min(1.0, urgency)
    )


# ============================================================
# CHARGER UTILIZATION PRESSURE
# ============================================================

def calculate_charger_pressure(
    ev: EV,
    current_minute: int
) -> float:
    """
    Compare required power against charger capacity.

    Example:

    Required = 9 kW
    Charger = 11 kW

    Pressure = 9 / 11
    """

    required_power = calculate_required_power(
        ev,
        current_minute
    )

    if required_power == float("inf"):
        return 1.0

    if ev.max_charging_power_kw <= 0:
        return 1.0

    pressure = (
        required_power
        / ev.max_charging_power_kw
    )

    return max(
        0.0,
        min(1.0, pressure)
    )


# ============================================================
# DEADLINE PRESSURE
# ============================================================

def calculate_deadline_pressure(
    ev: EV,
    current_minute: int
) -> float:
    """
    Convert feasibility ratio into urgency.

    The closer the EV is to becoming infeasible,
    the greater the pressure.
    """

    ratio = calculate_feasibility_ratio(
        ev,
        current_minute
    )

    if ratio == float("inf"):
        return 1.0

    # A ratio of 1 means the EV is at its
    # maximum theoretical charging requirement.
    pressure = ratio

    return max(
        0.0,
        min(1.0, pressure)
    )


# ============================================================
# OVERALL PRIORITY
# ============================================================

def calculate_priority(
    ev: EV,
    current_minute: int
) -> float:
    """
    V6 priority formula.

    Deadline feasibility receives the highest weight.

    Battery urgency       = 15%
    Departure urgency     = 20%
    Energy urgency        = 10%
    Charger pressure      = 20%
    Deadline pressure     = 35%
    """

    battery_urgency = calculate_battery_urgency(ev)

    departure_urgency = calculate_departure_urgency(
        ev,
        current_minute
    )

    energy_urgency = calculate_energy_urgency(ev)

    charger_pressure = calculate_charger_pressure(
        ev,
        current_minute
    )

    deadline_pressure = calculate_deadline_pressure(
        ev,
        current_minute
    )

    priority = (
        0.15 * battery_urgency
        + 0.20 * departure_urgency
        + 0.10 * energy_urgency
        + 0.20 * charger_pressure
        + 0.35 * deadline_pressure
    )

    return priority


# ============================================================
# EV ACTIVE CHECK
# ============================================================

def is_ev_active(
    ev: EV,
    current_minute: int
) -> bool:
    """
    Check whether EV is currently connected
    and still needs energy.
    """

    return (
        ev.arrival_minute <= current_minute
        and current_minute < ev.departure_minute
        and ev.current_soc < ev.target_soc
    )


# ============================================================
# DETERMINE EV CONDITION
# ============================================================

def determine_ev_condition(
    ev: EV,
    current_minute: int
) -> str:
    """
    Classify EV:

    WAITING
    CHARGING
    COMPLETED
    DEPARTED
    CRITICAL
    INFEASIBLE
    """

    if current_minute < ev.arrival_minute:
        return "WAITING"

    if current_minute >= ev.departure_minute:
        return "DEPARTED"

    if ev.current_soc >= ev.target_soc:
        return "COMPLETED"

    if not check_completion_feasibility(
        ev,
        current_minute
    ):
        return "INFEASIBLE"

    ratio = calculate_feasibility_ratio(
        ev,
        current_minute
    )

    if ratio >= 0.80:
        return "CRITICAL"

    return "FEASIBLE"


# ============================================================
# CHARGING POWER ALLOCATION
# ============================================================

def allocate_charging_power(
    evs: List[EV],
    current_minute: int,
    available_power_kw: float
):
    """
    Main V6 scheduling algorithm.

    Strategy:

    1. Find active EVs.
    2. Calculate deadline feasibility.
    3. Calculate required power.
    4. Calculate priority.
    5. Protect feasible critical EVs.
    6. Allocate according to deadline pressure.
    7. Use remaining capacity fairly.
    8. Never exceed charger limits.
    """

    # Reset allocations
    for ev in evs:

        ev.charging_power_kw = 0.0

        ev.charging_reason = (
            "No charging required"
        )

    # --------------------------------------------------------
    # Active EVs
    # --------------------------------------------------------

    active_evs = [
        ev
        for ev in evs
        if is_ev_active(
            ev,
            current_minute
        )
    ]

    if not active_evs:

        return

    if available_power_kw <= 0:

        for ev in active_evs:

            ev.charging_reason = (
                "No grid capacity available"
            )

        return

    # --------------------------------------------------------
    # Create scheduling information
    # --------------------------------------------------------

    scheduling_data = []

    for ev in active_evs:

        energy_required = calculate_energy_required(
            ev
        )

        required_power = calculate_required_power(
            ev,
            current_minute
        )

        priority = calculate_priority(
            ev,
            current_minute
        )

        feasibility_ratio = calculate_feasibility_ratio(
            ev,
            current_minute
        )

        deadline_slack = calculate_deadline_slack(
            ev,
            current_minute
        )

        condition = determine_ev_condition(
            ev,
            current_minute
        )

        # Desired power should never exceed charger limit.
        if required_power == float("inf"):

            desired_power = ev.max_charging_power_kw

        else:

            desired_power = min(
                required_power,
                ev.max_charging_power_kw
            )

        scheduling_data.append(
            {
                "ev": ev,
                "energy_required": energy_required,
                "required_power": required_power,
                "priority": priority,
                "feasibility_ratio": feasibility_ratio,
                "deadline_slack": deadline_slack,
                "condition": condition,
                "desired_power": desired_power
            }
        )

    # --------------------------------------------------------
    # V6 LOOK-AHEAD SORTING
    # --------------------------------------------------------
    #
    # Primary:
    #   Criticality
    #
    # Secondary:
    #   Priority
    #
    # Tertiary:
    #   Less deadline slack
    #
    # This prevents a comfortable EV from unnecessarily
    # consuming capacity needed by a deadline-critical EV.
    # --------------------------------------------------------

    scheduling_data.sort(
        key=lambda item: (
            item["condition"] == "CRITICAL",
            item["priority"],
            -item["deadline_slack"]
        ),
        reverse=True
    )

    remaining_power = available_power_kw

    # --------------------------------------------------------
    # PASS 1
    #
    # Protect EVs that are still feasible but close to
    # their deadline.
    # --------------------------------------------------------

    for item in scheduling_data:

        if remaining_power <= 0:
            break

        ev = item["ev"]

        condition = item["condition"]

        desired_power = item["desired_power"]

        if condition not in (
            "CRITICAL",
            "FEASIBLE"
        ):
            continue

        if desired_power <= 0:
            continue

        # Allocate the required average power where possible.
        assigned_power = min(
            desired_power,
            remaining_power
        )

        ev.charging_power_kw = assigned_power

        remaining_power -= assigned_power

        if condition == "CRITICAL":

            ev.charging_reason = (
                "Deadline-critical: "
                "charging prioritized to protect departure target"
            )

        else:

            ev.charging_reason = (
                "Deadline-feasible: "
                "charging allocated toward required average power"
            )

    # --------------------------------------------------------
    # PASS 2
    #
    # If power remains, give charging opportunity to
    # lower-priority EVs.
    # --------------------------------------------------------

    if remaining_power > 0:

        for item in scheduling_data:

            if remaining_power <= 0:
                break

            ev = item["ev"]

            if ev.charging_power_kw > 0:
                continue

            desired_power = item["desired_power"]

            if desired_power <= 0:
                continue

            assigned_power = min(
                desired_power,
                remaining_power
            )

            ev.charging_power_kw = assigned_power

            remaining_power -= assigned_power

            ev.charging_reason = (
                "Available capacity: "
                "charging allocated using remaining power"
            )

    # --------------------------------------------------------
    # PASS 3
    #
    # Anti-starvation.
    #
    # Give connected EVs a small charging opportunity
    # if capacity remains.
    # --------------------------------------------------------

    if remaining_power > 0:

        for item in scheduling_data:

            if remaining_power <= 0:
                break

            ev = item["ev"]

            if ev.charging_power_kw > 0:
                continue

            minimum_power = min(
                3.0,
                ev.max_charging_power_kw,
                item["desired_power"]
            )

            if minimum_power <= 0:
                continue

            assigned_power = min(
                minimum_power,
                remaining_power
            )

            ev.charging_power_kw = assigned_power

            remaining_power -= assigned_power

            ev.charging_reason = (
                "Fairness allocation: "
                "minimum charging opportunity"
            )

    # --------------------------------------------------------
    # FINAL SAFETY CAP
    # --------------------------------------------------------

    total_allocated = sum(
        ev.charging_power_kw
        for ev in evs
    )

    if total_allocated > available_power_kw:

        excess = (
            total_allocated
            - available_power_kw
        )

        # Reduce lower-priority EVs first.
        reduction_order = sorted(
            active_evs,
            key=lambda ev: calculate_priority(
                ev,
                current_minute
            )
        )

        for ev in reduction_order:

            if excess <= 0:
                break

            reduction = min(
                ev.charging_power_kw,
                excess
            )

            ev.charging_power_kw -= reduction

            excess -= reduction

    # --------------------------------------------------------
    # FINAL CHARGER LIMIT
    # --------------------------------------------------------

    for ev in active_evs:

        ev.charging_power_kw = min(
            ev.charging_power_kw,
            ev.max_charging_power_kw
        )


# ============================================================
# SOC UPDATE
# ============================================================

def update_ev_soc(
    ev: EV,
    interval_minutes: int
):
    """
    Update SOC after charging interval.
    """

    if ev.charging_power_kw <= 0:
        return

    energy_added = (
        ev.charging_power_kw
        * interval_minutes
        / 60
    )

    soc_increase = (
        energy_added
        / ev.battery_capacity_kwh
        * 100
    )

    ev.current_soc += soc_increase

    ev.current_soc = min(
        ev.current_soc,
        ev.target_soc
    )


# ============================================================
# TIME FORMATTING
# ============================================================

def format_time(
    simulation_minute: int
) -> str:

    base_hour = 8

    total_minutes = (
        base_hour * 60
        + simulation_minute
    )

    hour = (
        total_minutes // 60
    ) % 24

    minute = (
        total_minutes % 60
    )

    return f"{hour:02d}:{minute:02d}"


# ============================================================
# EV STATUS
# ============================================================

def print_ev_status(
    evs: List[EV],
    current_minute: int
):

    for ev in evs:

        condition = determine_ev_condition(
            ev,
            current_minute
        )

        print(
            f"  {ev.ev_id}: "
            f"SOC {ev.current_soc:.1f}% | "
            f"Power {ev.charging_power_kw:.2f} kW | "
            f"{condition}"
        )


# ============================================================
# SIMULATION STEP
# ============================================================

def run_simulation_step(
    evs: List[EV],
    current_minute: int,
    grid_limit_kw: float,
    building_demand_kw: float,
    solar_generation_kw: float,
    interval_minutes: int = 15
) -> Dict:

    # --------------------------------------------------------
    # Available grid capacity for EV charging
    # --------------------------------------------------------

    available_grid_power = max(
        0.0,
        grid_limit_kw
        - building_demand_kw
        + solar_generation_kw
    )

    # --------------------------------------------------------
    # Connected EVs
    # --------------------------------------------------------

    active_evs = [
        ev
        for ev in evs
        if is_ev_active(
            ev,
            current_minute
        )
    ]

    # --------------------------------------------------------
    # Physical charger capacity
    # --------------------------------------------------------

    charger_capacity = sum(
        ev.max_charging_power_kw
        for ev in active_evs
    )

    # Actual usable EV charging capacity
    available_power = min(
        available_grid_power,
        charger_capacity
    )

    # --------------------------------------------------------
    # Allocate charging
    # --------------------------------------------------------

    allocate_charging_power(
        evs,
        current_minute,
        available_power
    )

    # --------------------------------------------------------
    # Total EV power
    # --------------------------------------------------------

    total_ev_charging = sum(
        ev.charging_power_kw
        for ev in evs
    )

    # --------------------------------------------------------
    # Net grid load
    # --------------------------------------------------------

    net_grid_load = (
        building_demand_kw
        + total_ev_charging
        - solar_generation_kw
    )

    # --------------------------------------------------------
    # Safety check
    # --------------------------------------------------------

    if (
        net_grid_load
        <= grid_limit_kw + 1e-6
    ):

        grid_status = "SAFE"

    else:

        grid_status = "OVERLOAD"

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print("=" * 75)

    print(
        f"Time: "
        f"{format_time(current_minute)} "
        f"({current_minute} min)"
    )

    print(
        f"Building demand   : "
        f"{building_demand_kw:.2f} kW"
    )

    print(
        f"Solar generation  : "
        f"{solar_generation_kw:.2f} kW"
    )

    print(
        f"Grid limit        : "
        f"{grid_limit_kw:.2f} kW"
    )

    print(
        f"Available EV power: "
        f"{available_power:.2f} kW"
    )

    print("\nCharging allocation:")

    for ev in evs:

        if is_ev_active(
            ev,
            current_minute
        ):

            priority = calculate_priority(
                ev,
                current_minute
            )

            required_power = calculate_required_power(
                ev,
                current_minute
            )

            ratio = calculate_feasibility_ratio(
                ev,
                current_minute
            )

            condition = determine_ev_condition(
                ev,
                current_minute
            )

            if required_power == float("inf"):

                required_text = "INF"

            else:

                required_text = (
                    f"{required_power:.2f}"
                )

            if ratio == float("inf"):

                ratio_text = "INF"

            else:

                ratio_text = f"{ratio:.2f}"

            print(
                f"  {ev.ev_id}: "
                f"{ev.charging_power_kw:.2f} kW | "
                f"Priority {priority:.3f} | "
                f"Required {required_text} kW | "
                f"Feasibility {ratio_text} | "
                f"{condition}"
            )

            print(
                f"      Reason: "
                f"{ev.charging_reason}"
            )

    print(
        f"\nTotal EV charging : "
        f"{total_ev_charging:.2f} kW"
    )

    print(
        f"Net grid load     : "
        f"{net_grid_load:.2f} kW"
    )

    print(
        f"Grid status       : "
        f"{grid_status}"
    )

    # --------------------------------------------------------
    # SOC update
    # --------------------------------------------------------

    for ev in evs:

        update_ev_soc(
            ev,
            interval_minutes
        )

    print("\nEV status after interval:")

    print_ev_status(
        evs,
        current_minute
    )

    return {
        "time": format_time(current_minute),
        "building_demand_kw": building_demand_kw,
        "solar_generation_kw": solar_generation_kw,
        "available_power_kw": available_power,
        "total_ev_charging_kw": total_ev_charging,
        "net_grid_load_kw": net_grid_load,
        "grid_status": grid_status
    }


# ============================================================
# ORIGINAL STRESS-TEST EV DATA
# ============================================================

def create_stress_test_evs() -> List[EV]:

    return [

        EV(
            ev_id="EV-01",
            battery_capacity_kwh=60,
            current_soc=18,
            target_soc=80,
            arrival_minute=0,
            departure_minute=60,
            max_charging_power_kw=11
        ),

        EV(
            ev_id="EV-02",
            battery_capacity_kwh=75,
            current_soc=55,
            target_soc=80,
            arrival_minute=0,
            departure_minute=120,
            max_charging_power_kw=11
        ),

        EV(
            ev_id="EV-03",
            battery_capacity_kwh=60,
            current_soc=32,
            target_soc=80,
            arrival_minute=15,
            departure_minute=180,
            max_charging_power_kw=7
        ),

        EV(
            ev_id="EV-04",
            battery_capacity_kwh=50,
            current_soc=70,
            target_soc=90,
            arrival_minute=30,
            departure_minute=240,
            max_charging_power_kw=11
        ),

        EV(
            ev_id="EV-05",
            battery_capacity_kwh=80,
            current_soc=45,
            target_soc=90,
            arrival_minute=0,
            departure_minute=150,
            max_charging_power_kw=11
        )
    ]


# ============================================================
# FEASIBLE DEMO EV DATA
# ============================================================

def create_feasible_demo_evs() -> List[EV]:

    return [

        EV(
            ev_id="EV-01",
            battery_capacity_kwh=60,
            current_soc=40,
            target_soc=70,
            arrival_minute=0,
            departure_minute=120,
            max_charging_power_kw=11
        ),

        EV(
            ev_id="EV-02",
            battery_capacity_kwh=75,
            current_soc=55,
            target_soc=80,
            arrival_minute=0,
            departure_minute=150,
            max_charging_power_kw=11
        ),

        EV(
            ev_id="EV-03",
            battery_capacity_kwh=60,
            current_soc=50,
            target_soc=75,
            arrival_minute=15,
            departure_minute=180,
            max_charging_power_kw=11
        ),

        EV(
            ev_id="EV-04",
            battery_capacity_kwh=50,
            current_soc=70,
            target_soc=90,
            arrival_minute=30,
            departure_minute=240,
            max_charging_power_kw=11
        ),

        EV(
            ev_id="EV-05",
            battery_capacity_kwh=80,
            current_soc=55,
            target_soc=80,
            arrival_minute=0,
            departure_minute=180,
            max_charging_power_kw=11
        )
    ]


# ============================================================
# BUILDING DEMAND PROFILE
# ============================================================

def get_building_demand(
    current_minute: int
) -> float:

    profile = {

        0: 72,
        15: 76,
        30: 82,
        45: 88,

        60: 92,
        75: 84,
        90: 78,
        105: 74,

        120: 70,
        135: 68,
        150: 72,
        165: 76,

        180: 80,
        195: 75,
        210: 70,
        225: 68
    }

    return profile.get(
        current_minute,
        70
    )


# ============================================================
# SOLAR PROFILE
# ============================================================

def get_solar_generation(
    current_minute: int
) -> float:

    profile = {

        0: 12,
        15: 14,
        30: 18,
        45: 22,

        60: 28,
        75: 35,
        90: 40,
        105: 45,

        120: 50,
        135: 48,
        150: 42,
        165: 35,

        180: 28,
        195: 22,
        210: 16,
        225: 10
    }

    return profile.get(
        current_minute,
        10
    )


# ============================================================
# RUN SCENARIO
# ============================================================

def run_scenario(
    scenario_name: str,
    evs: List[EV]
):

    print("\n\n")

    print("#" * 75)

    print(
        f"SCENARIO: {scenario_name}"
    )

    print("#" * 75)

    grid_limit_kw = 100

    simulation_start = 0

    simulation_end = 225

    interval_minutes = 15

    results = []

    # --------------------------------------------------------
    # Simulation loop
    # --------------------------------------------------------

    for current_minute in range(
        simulation_start,
        simulation_end + 1,
        interval_minutes
    ):

        building_demand = get_building_demand(
            current_minute
        )

        solar_generation = get_solar_generation(
            current_minute
        )

        result = run_simulation_step(
            evs=evs,
            current_minute=current_minute,
            grid_limit_kw=grid_limit_kw,
            building_demand_kw=building_demand,
            solar_generation_kw=solar_generation,
            interval_minutes=interval_minutes
        )

        results.append(result)

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print("\n")

    print("#" * 75)

    print(
        f"FINAL REPORT: {scenario_name}"
    )

    print("#" * 75)

    target_reached = 0

    target_missed = 0

    total_energy_delivered = 0.0

    for ev in evs:

        remaining_energy = calculate_energy_required(
            ev
        )

        if ev.current_soc >= ev.target_soc:

            status = "TARGET REACHED"

            target_reached += 1

        else:

            status = "TARGET NOT REACHED"

            target_missed += 1

        energy_delivered = (
            ev.battery_capacity_kwh
            * (
                ev.current_soc
                - (
                    ev.current_soc
                    - (
                        ev.current_soc
                    )
                )
            )
        )

        print(
            f"\n{ev.ev_id}"
        )

        print(
            f"  Final SOC        : "
            f"{ev.current_soc:.1f}%"
        )

        print(
            f"  Target SOC       : "
            f"{ev.target_soc:.1f}%"
        )

        print(
            f"  Remaining energy : "
            f"{remaining_energy:.2f} kWh"
        )

        print(
            f"  Status           : "
            f"{status}"
        )

        # Maximum achievable SOC at departure.
        maximum_soc = calculate_max_achievable_soc(
            ev,
            ev.departure_minute
        )

        # At/after departure this calculation gives current
        # SOC, so use it mainly as a diagnostic.
        print(
            f"  Final assessment  : "
            f"{status}"
        )

        if status == "TARGET NOT REACHED":

            print(
                "  Explanation      : "
                "Target was not achieved before departure."
            )

    # --------------------------------------------------------
    # Grid safety statistics
    # --------------------------------------------------------

    overload_steps = sum(
        1
        for result in results
        if result["grid_status"] == "OVERLOAD"
    )

    safe_steps = len(results) - overload_steps

    peak_grid_load = max(
        result["net_grid_load_kw"]
        for result in results
    )

    print("\n")

    print("-" * 75)

    print("SIMULATION SUMMARY")

    print("-" * 75)

    print(
        f"EVs reaching target : "
        f"{target_reached}/{len(evs)}"
    )

    print(
        f"EVs missing target  : "
        f"{target_missed}/{len(evs)}"
    )

    print(
        f"Safe intervals      : "
        f"{safe_steps}/{len(results)}"
    )

    print(
        f"Overload intervals  : "
        f"{overload_steps}"
    )

    print(
        f"Peak net grid load  : "
        f"{peak_grid_load:.2f} kW"
    )

    print(
        "Grid constraint     : "
        "ENFORCED"
    )

    print(
        "Deadline awareness  : "
        "ENABLED"
    )

    print(
        "Look-ahead logic    : "
        "ENABLED"
    )

    print(
        "Solar-aware charging: "
        "ENABLED"
    )

    print(
        "Fairness mechanism  : "
        "ENABLED"
    )

    return results


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")

    print("=" * 75)

    print(
        "SMART EV CHARGING & LOCAL GRID MANAGEMENT"
    )

    print(
        "OPTIMIZER VERSION 6"
    )

    print(
        "Deadline-Feasible + Look-Ahead + Solar-Aware"
    )

    print("=" * 75)

    # ========================================================
    # SCENARIO 1
    # Original difficult stress test
    # ========================================================

    stress_evs = create_stress_test_evs()

    run_scenario(
        "ORIGINAL STRESS TEST",
        stress_evs
    )

    # ========================================================
    # SCENARIO 2
    # Feasible charging scenario
    # ========================================================

    feasible_evs = create_feasible_demo_evs()

    run_scenario(
        "FEASIBLE SMART-CHARGING TEST",
        feasible_evs
    )


# ============================================================
# PROGRAM ENTRY
# ============================================================

if __name__ == "__main__":

    main()
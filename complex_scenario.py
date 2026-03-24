from disaster_scenario import generate_domain_actions
from domain_models import State

Fact = tuple[str, ...]

LOCATIONS = ["A", "B", "C", "D", "E", "F"]
RESOURCES = ["Bulldozer1", "MedTeam1", "MedTeam2"]
UNDIRECTED_ROADS = [("A", "B"), ("B", "C"), ("C", "D"), ("B", "E"), ("C", "F")]
DIRECTIONAL_ROADS = [(source, target) for source, target in UNDIRECTED_ROADS] + [
    (target, source) for source, target in UNDIRECTED_ROADS
]

all_possible_actions = generate_domain_actions(LOCATIONS, RESOURCES, DIRECTIONAL_ROADS)

_connected_facts: list[Fact] = [
    ("connected", source, target) for source, target in DIRECTIONAL_ROADS
]
_clear_facts: list[Fact] = [
    ("clear", "A", "B"),
    ("clear", "B", "A"),
    ("clear", "B", "C"),
    ("clear", "C", "B"),
    ("clear", "C", "D"),
    ("clear", "D", "C"),
]
_blocked_facts: list[Fact] = [
    ("blocked", "B", "E"),
    ("blocked", "E", "B"),
    ("blocked", "C", "F"),
    ("blocked", "F", "C"),
]
_resource_facts: list[Fact] = [
    ("at", "Bulldozer1", "A"),
    ("at", "MedTeam1", "D"),
    ("at", "MedTeam2", "A"),
]
_victim_facts: list[Fact] = [("victims_untreated", "E"), ("victims_untreated", "F")]

initial_facts = frozenset(
    _connected_facts + _clear_facts + _blocked_facts + _resource_facts + _victim_facts
)
initial_state = State(initial_facts)
goal_conditions = frozenset({("victims_treated", "E"), ("victims_treated", "F")})
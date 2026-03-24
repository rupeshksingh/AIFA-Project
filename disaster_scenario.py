from collections.abc import Iterable, Sequence

from domain_models import Action, State

Fact = tuple[str, ...]
Road = tuple[str, str]


def _fact(*parts: str) -> Fact:
    return tuple(parts)


def _expand_undirected_edges(edges: Iterable[Road]) -> list[Road]:
    """Convert undirected links to directional edges."""
    directed: list[Road] = []
    for source, target in edges:
        directed.append((source, target))
        directed.append((target, source))
    return directed


def generate_domain_actions(
    locations: Sequence[str],
    resources: Sequence[str],
    directional_roads: Sequence[Road] | None = None,
) -> list[Action]:
    """
    Generate all domain operators for the provided map and resources.

    If `directional_roads` is omitted, operators are generated for every ordered
    location pair to preserve backward compatibility.
    """
    if directional_roads is None:
        directional_roads = [
            (loc_from, loc_to)
            for loc_from in locations
            for loc_to in locations
            if loc_from != loc_to
        ]

    actions: list[Action] = []
    bulldozers = [resource for resource in resources if resource.startswith("Bulldozer")]
    medical_teams = [resource for resource in resources if resource.startswith("MedTeam")]

    for resource in resources:
        for loc_from, loc_to in directional_roads:
            preconditions = frozenset(
                {
                    _fact("at", resource, loc_from),
                    _fact("connected", loc_from, loc_to),
                    _fact("clear", loc_from, loc_to),
                }
            )
            add_effects = frozenset({_fact("at", resource, loc_to)})
            del_effects = frozenset({_fact("at", resource, loc_from)})
            actions.append(
                Action(
                    "Move",
                    (resource, loc_from, loc_to),
                    preconditions,
                    add_effects,
                    del_effects,
                )
            )

    for resource in bulldozers:
        for loc_from, loc_to in directional_roads:
            preconditions = frozenset(
                {
                    _fact("at", resource, loc_from),
                    _fact("connected", loc_from, loc_to),
                    _fact("blocked", loc_from, loc_to),
                }
            )
            add_effects = frozenset(
                {
                    _fact("clear", loc_from, loc_to),
                    _fact("clear", loc_to, loc_from),
                }
            )
            del_effects = frozenset(
                {
                    _fact("blocked", loc_from, loc_to),
                    _fact("blocked", loc_to, loc_from),
                }
            )
            actions.append(
                Action(
                    "Clear",
                    (resource, loc_from, loc_to),
                    preconditions,
                    add_effects,
                    del_effects,
                )
            )

    for resource in medical_teams:
        for location in locations:
            preconditions = frozenset(
                {
                    _fact("at", resource, location),
                    _fact("victims_untreated", location),
                }
            )
            add_effects = frozenset({_fact("victims_treated", location)})
            del_effects = frozenset({_fact("victims_untreated", location)})
            actions.append(
                Action(
                    "Treat",
                    (resource, location),
                    preconditions,
                    add_effects,
                    del_effects,
                )
            )

    return actions


LOCATIONS = ["A", "B", "C"]
RESOURCES = ["Bulldozer1", "MedTeam1"]
UNDIRECTED_ROADS = [("A", "B"), ("B", "C")]
DIRECTIONAL_ROADS = _expand_undirected_edges(UNDIRECTED_ROADS)

all_possible_actions = generate_domain_actions(LOCATIONS, RESOURCES, DIRECTIONAL_ROADS)

_connected_facts: list[Fact] = [
    _fact("connected", source, target) for source, target in DIRECTIONAL_ROADS
]
_clear_facts: list[Fact] = [_fact("clear", "A", "B"), _fact("clear", "B", "A")]
_blocked_facts: list[Fact] = [_fact("blocked", "B", "C"), _fact("blocked", "C", "B")]
_resource_facts: list[Fact] = [_fact("at", "Bulldozer1", "A"), _fact("at", "MedTeam1", "A")]
_victim_facts: list[Fact] = [_fact("victims_untreated", "C")]

initial_facts = frozenset(
    _connected_facts + _clear_facts + _blocked_facts + _resource_facts + _victim_facts
)
initial_state = State(initial_facts)
goal_conditions = frozenset({_fact("victims_treated", "C")})
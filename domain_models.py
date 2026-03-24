from dataclasses import dataclass


@dataclass(frozen=True)
class State:
    facts: frozenset[tuple[str, ...]]

    def satisfies(self, conditions: frozenset[tuple[str, ...]]) -> bool:
        """Check if all given conditions are present in the current state."""
        return conditions.issubset(self.facts)

    def apply_effects(
        self,
        add_effects: frozenset[tuple[str, ...]],
        del_effects: frozenset[tuple[str, ...]],
    ) -> "State":
        """Generate a new state by adding and removing specific facts."""
        new_facts = set(self.facts)
        new_facts.difference_update(del_effects)
        new_facts.update(add_effects)
        return State(frozenset(new_facts))


@dataclass
class Action:
    name: str
    parameters: tuple[str, ...]
    preconditions: frozenset[tuple[str, ...]]
    add_effects: frozenset[tuple[str, ...]]
    del_effects: frozenset[tuple[str, ...]]

    def is_applicable(self, state: State) -> bool:
        """An action is applicable if the state satisfies all its preconditions."""
        return state.satisfies(self.preconditions)

    def execute(self, state: State) -> State:
        """Returns the new state after the action is applied."""
        return state.apply_effects(self.add_effects, self.del_effects)

    def __str__(self) -> str:
        return f"{self.name}({', '.join(self.parameters)})"

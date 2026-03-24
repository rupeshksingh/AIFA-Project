from domain_models import Action, State


def test_state_apply_effects_creates_new_state() -> None:
    initial = State(
        frozenset(
            {
                ("at", "MedTeam1", "A"),
                ("victims_untreated", "C"),
            }
        )
    )
    next_state = initial.apply_effects(
        add_effects=frozenset({("victims_treated", "C")}),
        del_effects=frozenset({("victims_untreated", "C")}),
    )

    assert initial is not next_state
    assert ("victims_untreated", "C") in initial.facts
    assert ("victims_untreated", "C") not in next_state.facts
    assert ("victims_treated", "C") in next_state.facts


def test_action_is_applicable_and_execute() -> None:
    state = State(
        frozenset(
            {
                ("at", "MedTeam1", "C"),
                ("victims_untreated", "C"),
            }
        )
    )
    action = Action(
        name="Treat",
        parameters=("MedTeam1", "C"),
        preconditions=frozenset({("at", "MedTeam1", "C"), ("victims_untreated", "C")}),
        add_effects=frozenset({("victims_treated", "C")}),
        del_effects=frozenset({("victims_untreated", "C")}),
    )

    assert action.is_applicable(state)
    post_state = action.execute(state)
    assert ("victims_treated", "C") in post_state.facts
    assert ("victims_untreated", "C") not in post_state.facts

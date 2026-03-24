from collections.abc import Collection, Iterable

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.axes import Axes

Fact = tuple[str, ...]
StateFacts = Collection[Fact]


def _render_world_state(ax: Axes, state_facts: StateFacts, step_title: str = "World State") -> None:
    """Render one world state as a labeled road-network graph."""
    G = nx.Graph()
    node_labels = {}
    edge_colors = []

    for fact in state_facts:
        if fact[0] == "connected":
            G.add_edge(fact[1], fact[2])
        elif fact[0] == "at":
            # Keep only map locations as nodes, never resources.
            G.add_node(fact[2])
        elif fact[0] in ("victims_untreated", "victims_treated"):
            G.add_node(fact[1])

    for node in G.nodes():
        node_labels[node] = node

    for u, v in G.edges():
        color = "grey"
        if ("blocked", u, v) in state_facts or ("blocked", v, u) in state_facts:
            color = "red"
        elif ("clear", u, v) in state_facts or ("clear", v, u) in state_facts:
            color = "green"
        edge_colors.append(color)

    for fact in state_facts:
        if fact[0] == "at":
            resource, location = fact[1], fact[2]
            node_labels[location] += f"\n[{resource}]"
        elif fact[0] == "victims_untreated":
            node_labels[fact[1]] += "\n(Victims: UNTREATED)"
        elif fact[0] == "victims_treated":
            node_labels[fact[1]] += "\n(Victims: TREATED)"

    ax.clear()
    ax.set_title(step_title, fontsize=14, fontweight="bold")

    pos = nx.spring_layout(G, seed=42)
    nx.draw(
        G,
        pos,
        ax=ax,
        with_labels=False,
        node_color="lightblue",
        node_size=3000,
        edge_color=edge_colors,
        width=3,
    )

    safe_labels = {k: v for k, v in node_labels.items() if k in pos}
    nx.draw_networkx_labels(G, pos, labels=safe_labels, font_size=10, ax=ax)

    red_line = mlines.Line2D([], [], color="red", linewidth=3, label="Blocked Road")
    green_line = mlines.Line2D([], [], color="green", linewidth=3, label="Clear Road")
    ax.legend(
        handles=[red_line, green_line],
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        borderaxespad=0.0,
    )


def draw_world_state(state_facts: StateFacts, step_title: str = "World State") -> None:
    """Draw one state in a single blocking figure."""
    fig, ax = plt.subplots(figsize=(9, 6))
    _render_world_state(ax, state_facts, step_title)
    fig.tight_layout(rect=(0.0, 0.0, 0.82, 1.0))
    plt.show()


def play_world_states(
    states_with_titles: Iterable[tuple[StateFacts, str]],
    pause_seconds: float = 1.0,
) -> None:
    """Play multiple states in a single figure; stop if window is closed."""
    states_with_titles = list(states_with_titles)
    if not states_with_titles:
        return

    fig, ax = plt.subplots(figsize=(9, 6))
    plt.ion()
    try:
        for state_facts, step_title in states_with_titles:
            if not plt.fignum_exists(fig.number):
                break
            _render_world_state(ax, state_facts, step_title)
            fig.tight_layout(rect=(0.0, 0.0, 0.82, 1.0))
            plt.pause(pause_seconds)
    finally:
        plt.ioff()

    if plt.fignum_exists(fig.number):
        plt.show()
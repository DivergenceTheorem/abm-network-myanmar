import argparse
import itertools
import re
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DEFAULT_CSV = HERE / "myanmar_data.csv"
DEFAULT_OUT = HERE / "networks"

EVENT_TYPES = ["Battles", "Strategic developments"]
COLUMNS = ["event_date", "event_type", "actor1", "assoc_actor_1", "actor2", "assoc_actor_2"]
TOP_N = 50


# Non-combatant groups: ACLED names them "<Group> (<Country>)", e.g. "Women (Myanmar)".
NON_COMBATANT = re.compile(
    r"\((Myanmar|China|North Korea|South Korea|Hong Kong|Japan|Taiwan|Mongolia|Bangladesh|India|"
    r"Pakistan|Thailand|Vietnam|Philippines|Indonesia|Kyrgyzstan|Ethiopia|Uganda|"
    r"United States|United Kingdom|International)\)$"
)
# Armed groups that share that suffix and must be kept.
ARMED_KEYWORDS = re.compile(r"Militia|Security Forces")
# Catch-all labels that don't identify a real actor.
UNIDENTIFIED = re.compile(r"Unidentified")


# --- Data loading ---

def is_excluded(actor):
    """True for actors left out of the networks: non-combatant groups and unidentified catch-alls."""
    if UNIDENTIFIED.search(actor):
        return True
    if NON_COMBATANT.search(actor) and not ARMED_KEYWORDS.search(actor):
        return True
    return False


def load_events(csv_path=DEFAULT_CSV, event_types=EVENT_TYPES):
    """Load ACLED data, keep relevant columns and event types."""
    df = pd.read_csv(csv_path, usecols=COLUMNS)
    return df[df["event_type"].isin(event_types)].reset_index(drop=True)


def parse_actors(main_actor, assoc_actor):
    """Return the unique, ordered list of armed actors on one side of an event."""
    actors = []
    if pd.notna(main_actor) and str(main_actor).strip():
        actors.append(str(main_actor).strip())
    if pd.notna(assoc_actor) and str(assoc_actor).strip():
        actors.extend(a.strip() for a in str(assoc_actor).split(";") if a.strip())
    actors = [a for a in actors if not is_excluded(a)]
    return list(dict.fromkeys(actors))  # dedupe, preserve order


def event_sides(df):
    """List of (side1, side2) actor lists, one per event."""
    return [
        (parse_actors(a1, s1), parse_actors(a2, s2))
        for a1, s1, a2, s2 in zip(df["actor1"], df["assoc_actor_1"], df["actor2"], df["assoc_actor_2"])
    ]


# --- Network construction ---

def count_actors(sides):
    """How many events each actor appears in (either side)."""
    counter = Counter()
    for side1, side2 in sides:
        counter.update(side1)
        counter.update(side2)
    return counter


def count_relations(sides, actors):
    """Count same-side (friend) and opposite-side (enemy) co-occurrences among `actors`."""
    friend_counts = defaultdict(int)
    enemy_counts = defaultdict(int)

    for side1, side2 in sides:
        s1 = sorted({a for a in side1 if a in actors})
        s2 = sorted({a for a in side2 if a in actors})

        for side in (s1, s2):
            for pair in itertools.combinations(side, 2):
                friend_counts[pair] += 1

        for a in s1:
            for b in s2:
                if a != b:
                    enemy_counts[tuple(sorted((a, b)))] += 1

    return friend_counts, enemy_counts


def classify_edges(friend_counts, enemy_counts):
    """Keep pairs that are purely friends or purely enemies; drop mixed pairs."""
    friend_edges, enemy_edges = [], []
    for pair in set(friend_counts) | set(enemy_counts):
        f, e = friend_counts.get(pair, 0), enemy_counts.get(pair, 0)
        if f > 0 and e == 0:
            friend_edges.append((*pair, f))
        elif e > 0 and f == 0:
            enemy_edges.append((*pair, e))
    return friend_edges, enemy_edges


def build_networks(df, top_n=TOP_N):
    """Return (conflict_graph, friendship_graph) over the top_n most active actors (None = all)."""
    sides = event_sides(df)
    actor_counter = count_actors(sides)
    ranked = [a for a, _ in actor_counter.most_common(top_n)]
    top = set(ranked)

    friend_counts, enemy_counts = count_relations(sides, top)
    friend_edges, enemy_edges = classify_edges(friend_counts, enemy_counts)

    def make_graph(edges, relation):
        G = nx.Graph(relation=relation)
        for rank, actor in enumerate(ranked, start=1):
            G.add_node(actor, events=actor_counter[actor], rank=rank)
        G.add_weighted_edges_from(edges)
        return G

    return make_graph(enemy_edges, "conflict"), make_graph(friend_edges, "friendship")


# --- Output ---

def save_network(G, out_dir, name):
    """Save a graph as GraphML plus an edge-list CSV."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(G, out_dir / f"{name}.graphml")
    edges = nx.to_pandas_edgelist(G).sort_values("weight", ascending=False)
    edges.to_csv(out_dir / f"{name}_edges.csv", index=False)


def plot_network(G, title, edge_color, ax=None, n_color_groups=6):
    """Draw a network; nodes coloured by activity-rank group."""
    import matplotlib.pyplot as plt

    palette = ["skyblue", "lightgreen", "gold", "violet", "salmon", "turquoise"][:n_color_groups]
    group_size = -(-G.number_of_nodes() // len(palette))  # ceil division
    node_colors = [palette[(G.nodes[n]["rank"] - 1) // group_size] for n in G.nodes]

    if ax is None:
        _, ax = plt.subplots(figsize=(12, 10))
    pos = nx.spring_layout(G, seed=42, k=4)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color=edge_color, alpha=0.9, ax=ax)
    ax.set_title(title, fontsize=16)
    ax.axis("off")
    return ax


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Path to ACLED Myanmar CSV")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output directory")
    parser.add_argument("--top-n", type=int, default=TOP_N, help="Number of most active actors to keep (0 = all)")
    parser.add_argument("--plot", action="store_true", help="Also save PNG plots of both networks")
    args = parser.parse_args()

    df = load_events(args.csv)
    top_n = args.top_n or None
    print(f"Unique armed actors: {len(count_actors(event_sides(df)))}")
    conflict_G, friendship_G = build_networks(df, top_n=top_n)

    for G, name, color in [(conflict_G, "conflict", "red"), (friendship_G, "friendship", "green")]:
        save_network(G, args.out, name)
        print(f"{name:>10}: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        if args.plot:

            ax = plot_network(G, f"{f'Top-{top_n}' if top_n else 'All'} Actor {name.title()} Network", color)
            ax.figure.savefig(Path(args.out) / f"{name}.png", dpi=150, bbox_inches="tight")
            plt.close(ax.figure)

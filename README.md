# How Local Incentives Shape Conflict Network Formation: An Agent-Based Study of the Myanmar Civil War

Code and data for **Kurmanov & Melo Ponce (2026)**, presented at the *Shaping Asia's Future: Development, Innovation, and Society in Transition* conference (Nazarbayev University, April 2026). The poster and slides are in [SAF26-conference/](SAF26-conference/).

This project uses agent-based modeling to investigate why armed conflict actors in transitional Asian societies form stable coalition networks that generate collective welfare losses. By simulating decentralized strategic interactions among heterogeneous agents with limited information, it examines how local incentives, rivalries, and resource competition affect the emergence of inefficient conflict networks.

Analytical models of conflict networks, such as König et al. (2017), take the network of alliances and enmities as fixed and solve for equilibrium. Here the network is instead allowed to emerge and change. Agents placed on a grid approximation of Myanmar compete for resource-bearing tiles, using only what they can see within their vision radius. Contesting a tile creates an enmity link. Forming an alliance lowers the cost of conflict but means sharing resources.

The model starts from the real network of alliances and enmities, built from ACLED event data. **This repository currently contains that empirical step.** The grid simulation is still in development (see [Project status](#project-status)).

| Network | Edge rule | Actors | Edges |
|---|---|---|---|
| Conflict (enmity) | Fought on opposite sides at least once, never on the same side | Top 50 | 172 |
| Friendship (alliance) | Fought on the same side at least once, never on opposite sides | Top 50 | 149 |

The data covers ACLED events in Myanmar from 5 May 2021 to 17 March 2025.

---

## Repository layout

```
.
├── requirements.txt                # pinned Python dependencies
├── SAF26-conference/
│   ├── ABM_Myanmar_Poster.pdf      # conference poster
│   └── ABM_Myanmar_Presentation.pdf
└── myanmar_data/
    ├── myanmar_data.csv            # ACLED event data (39,663 events)
    ├── build_networks.py           # builds the conflict and friendship networks
    ├── EDA.ipynb                   # exploratory analysis and network plots
    └── networks/                   # output of build_networks.py
        ├── conflict.graphml
        ├── conflict_edges.csv
        ├── friendship.graphml
        └── friendship_edges.csv
```

---

## 1. Environment setup

The code has been run with **Python 3.13**. A virtual environment is recommended.

```bash
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate

pip install -r requirements.txt
```

Pinned versions (from [requirements.txt](requirements.txt)):

| Package | Version | Used for |
|---|---|---|
| networkx | 3.6.1 | graphs, GraphML export, layout |
| pandas | 2.3.3 | loading ACLED data, edge-list export |
| numpy | 2.4.4 | dependency of pandas and networkx |
| matplotlib | 3.10.9 | network plots |
| ipykernel | 7.2.0 | running `EDA.ipynb` |

---

## 2. Build the networks

Run from the repository root or from inside `myanmar_data/`. Paths are resolved relative to the script, so both work.

```bash
python myanmar_data/build_networks.py            # top-50 actors, writes to myanmar_data/networks/
python myanmar_data/build_networks.py --plot     # also saves conflict.png and friendship.png
python myanmar_data/build_networks.py --top-n 0  # use every actor instead of the top 50
```

| Option | Default | Meaning |
|---|---|---|
| `--csv` | `myanmar_data/myanmar_data.csv` | ACLED input file |
| `--out` | `myanmar_data/networks/` | output directory |
| `--top-n` | 50 | number of most active actors to keep (`0` = all) |
| `--plot` | off | also save PNG plots of both networks |

The script prints the number of unique armed actors and the size of each network.

```
Unique armed actors: 2738
  conflict: 50 nodes, 172 edges
friendship: 50 nodes, 149 edges
```

The functions can also be imported, which is what the notebook does:

```python
import build_networks as bn

events = bn.load_events("myanmar_data.csv")
conflict_G, friendship_G = bn.build_networks(events, top_n=50)
```

### Exploratory notebook

[myanmar_data/EDA.ipynb](myanmar_data/EDA.ipynb) walks through the same pipeline step by step. It shows event types, the most active actors, how many actors pass each activity threshold, the strongest ties, and plots of both networks. Open it from inside `myanmar_data/`, because it reads `myanmar_data.csv` by relative path.

---

## 3. What the code does

### Events

Only events located in **Myanmar** (ACLED `country` column) of type **Battles** or **Strategic developments** are kept. Violence against civilians is one-sided, so it carries no information about ties between armed actors.

Each event has two sides. Side 1 is `actor1` plus `assoc_actor_1`, and side 2 is `actor2` plus `assoc_actor_2`. Associated actors are `;`-separated in ACLED, and duplicates within a side are removed.

### Actor filtering (`is_excluded`)

Two kinds of actor are dropped before anything is counted:

1. **Non-combatant groups.** ACLED names civilian, occupational, religious and ethnic groups as `<Group> (<Country>)`, for example `Women (Myanmar)`, `Teachers (Myanmar)` or `Civilians (China)`. Names that also contain `Militia` or `Security Forces` are armed and are kept.
2. **Unidentified actors**, such as `Unidentified Anti-Coup Armed Group`. These are catch-all labels, not single organisations.

This leaves **2,738** unique armed actors. A dropped actor is removed only from its own side, so the event still counts for the actors that remain.

### Top-N selection

Actors are ranked by the number of events they appear in. Most are very small: 757 appear in only one event, and only 125 appear in 50 or more. The default keeps the **top 50**, which account for 68% of all actor appearances. The full network (`--top-n 0`) is too dense to plot readably, and many of its edges come from a single event.

### Edge rule

For every pair of selected actors, the script counts

- **same-side** events, where both appear on the same side, and
- **opposite-side** events, where they appear on different sides.

A pair is a **friendship** edge if it has same-side events and no opposite-side events, and a **conflict** edge if the reverse holds. Pairs with both are ambiguous and get no edge in either network. The edge weight is the number of events behind the edge.

### Node colours in the plots

Nodes are coloured in six groups by activity rank (ranks 1–9, 10–18, …). The layout is `networkx.spring_layout` with `seed=42`.

---

## 4. Reproducibility notes

- **Determinism.** The network construction involves no randomness, so the same input CSV always gives the same networks. The plot layout is seeded and is also reproducible with the pinned networkx version.
- **Data snapshot.** `myanmar_data.csv` is a fixed ACLED export. ACLED revises past events and adds new ones, so a fresh download will give somewhat different numbers.
- **Countries.** The export also contains events located in China, North Korea, South Korea and Taiwan (818 of 39,663). `load_events` drops them. Pass `country=` to change this.

---

## 5. Output data dictionary

### `conflict_edges.csv`, `friendship_edges.csv`

One row per edge, sorted by weight (descending).

| Column | Meaning |
|---|---|
| `source`, `target` | ACLED actor names. The graph is undirected, so the order means nothing. |
| `weight` | Number of opposite-side events (conflict) or same-side events (friendship) between the two actors. |

### `conflict.graphml`, `friendship.graphml`

The same networks, including every top-N actor as a node, even actors with no edges. Load with `networkx.read_graphml`.

| Attribute | Level | Meaning |
|---|---|---|
| `events` | node | Number of events the actor appears in, after filtering. |
| `rank` | node | Activity rank (1 = most active). |
| `weight` | edge | As in the edge-list CSV. |
| `relation` | graph | `conflict` or `friendship`. |

---

## Project status

The full agent-based model is still in progress. Its planned design, from the poster and slides:

- **Grid.** Myanmar is approximated by a square grid. Each tile has a resource endowment based on the real distribution of natural resources, manpower and fertile land.
- **Agents.** The five most influential actors are placed on the grid at their real locations. Their initial ties come from the ACLED networks in this repository.
- **Dynamics.** Each agent moves to the tile within its vision radius that maximises its utility. An uncontested tile is occupied and its resources are shared with allies. A contested tile triggers a conflict, whose cost depends on each side's resources and alliances, and creates an enmity link. Agents have incomplete information about each other, so they can choose to fight and lose.
- **Alliances.** Allies share resources and the cost of losing. An agent leaves an alliance when it becomes too costly, and enmity links can dissolve when cooperation pays.

Current work is on the spatial discretisation of the grid and on an econometric analysis of how armed conflict affects resource spending among competing actors.

---

## Data source

Event data comes from the **Armed Conflict Location & Event Data Project (ACLED)**, <https://acleddata.com>. Use of the data is subject to ACLED's terms of use.

---

## Citation

If you use this code, please cite:

> Kurmanov, M., & Melo Ponce, A. (2026). *How Local Incentives Shape Conflict Network Formation: An Agent-Based Study of the Myanmar Civil War.* Shaping Asia's Future Conference, Nazarbayev University.

Code: <https://github.com/DivergenceTheorem/abm-network-myanmar>

### References

- König, M. D., Rohner, D., Thoenig, M., & Zilibotti, F. (2017). Networks in conflict: Theory and evidence from the great war of Africa. *Econometrica*, 85(4), 1093–1132.

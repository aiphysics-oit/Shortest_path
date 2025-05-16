from __future__ import annotations
import itertools, re, pickle, subprocess, sys
from pathlib import Path
import networkx as nx
import graphviz
import igraph as ig
from itertools import combinations

# ---------- 定数 ------------------------------------------------------
W_BLACK = 1.0   # L1 weight
W_RED   = 1.0   # L2 weight (赤)
W_BLUE  = 0.5   # 同一 L2 dotted weight (青)

PEN_L1 = "3.0"   # L1 最短経路線幅
PEN_L2 = "2.0"   # L2 追加エッジ線幅

# ---------- グラフ構築ロジック ----------------------------------------

def auto_prefix(l1l2_path: Path) -> str:
    """ファイル名 (xxxxxx_L1-L2_DB.txt) から数値プレフィックスを返す"""
    m = re.match(r"(\d+)_L1-L2_DB", l1l2_path.stem)
    return m.group(1) if m else "graph"


def build_graph(l1l2_path: Path, l2_path: Path) -> tuple[ig.Graph, dict[int, str], dict[int, str]]:
    lines = l1l2_path.read_text(encoding="utf-8").splitlines()
    n_nodes = int(lines[0].split()[0])

    ig_g = ig.Graph(directed=False)
    ig_g.add_vertices(n_nodes)
    for i in range(n_nodes):
        ig_g.vs[i]["name"] = i

    node_labels = {}
    L2code_to_L1num = {}
    L1num_to_L2code = {}

    for ln in lines[1:1 + n_nodes]:
        nid = int(ln.split()[0])
        L1s = ln.find("L1 |") + len("L1 |")
        L1e = ln.find("L2")
        l1_label = ln[L1s:L1e].strip().replace("|", "\n")
        L2s = ln.find("L2 |") + len("L2 |")
        L2e = ln.find("#", L2s)
        l2_label = ln[L2s:L2e].strip()
        label = f"# {nid}\n{l1_label}\n{l2_label}"
        ig_g.vs[nid]["label"] = label
        node_labels[nid] = label
        L2code_to_L1num.setdefault(l2_label, []).append(nid)
        L1num_to_L2code[nid] = l2_label

    # 黒エッジ
    idx_edges = next(i + 1 for i, ln in enumerate(lines) if "# number of l1 edges" in ln.lower())
    for ln in lines[idx_edges:]:
        sp = ln.split()
        if len(sp) < 2 or not sp[0].isdigit():
            continue
        u, v = map(int, sp[:2])
        ig_g.add_edge(u, v)
        ig_g.es[-1]["color"] = "black"
        ig_g.es[-1]["weight"] = W_BLACK
    print("black")

    # 既存エッジ記録（赤と青の処理高速化用）
    existing_edges = set(map(tuple, map(sorted, ig_g.get_edgelist())))

    # L2情報読み込み
    lines = l2_path.read_text(encoding="utf-8").splitlines()
    n_l2_nodes = int(lines[0].split()[0])
    L2num_to_code = {
        int(ln.split()[0]): ln[ln.find("L2 |") + len("L2 |"): ln.find("Connected")].strip()
        for ln in lines[1:1 + n_l2_nodes]
    }

    idx_edges = next(i + 1 for i, ln in enumerate(lines) if "# number of l2 edges" in ln.lower())
    for ln in lines[idx_edges:]:
        sp = ln.split()
        if len(sp) < 3 or not sp[0].isdigit():
            continue
        a, b = map(int, sp[1:3])
        la, lb = L2num_to_code.get(a), L2num_to_code.get(b)
        if la is None or lb is None:
            continue
        for u in L2code_to_L1num.get(la, []):
            for v in L2code_to_L1num.get(lb, []):
                if u == v:
                    continue
                edge = tuple(sorted((u, v)))
                if edge not in existing_edges:
                    ig_g.add_edge(u, v)
                    ig_g.es[-1]["color"] = "red"
                    ig_g.es[-1]["weight"] = W_RED
                    existing_edges.add(edge)
    print("red")

    # 青エッジ（同じL2ラベルのノード間、未接続のみ）
    for nodes in L2code_to_L1num.values():
        if len(nodes) > 100:  # オプション: 組合せ爆発回避
            continue
        for u, v in combinations(nodes, 2):
            edge = tuple(sorted((u, v)))
            if edge not in existing_edges:
                ig_g.add_edge(u, v)
                ig_g.es[-1]["color"] = "blue"
                ig_g.es[-1]["weight"] = W_BLUE
                ig_g.es[-1]["style"] = "dotted"
                existing_edges.add(edge)
    print("blue")

    return ig_g, node_labels, L1num_to_L2code


def write_edge_lists(G: ig.Graph, out_path: str = "all_edges.txt") -> None:
    """igraphグラフ G から色別エッジ一覧を out_path に保存"""

    black_edges, red_edges, blue_edges = [], [], []
    for e in G.es:
        u, v = e.source, e.target
        col = e["color"] if "color" in e.attributes() else ""
        if col == "black":
            black_edges.append((u, v))
        elif col == "red":
            red_edges.append((u, v))
        elif col == "blue":
            blue_edges.append((u, v))

    def format_edges(edge_list: list[tuple[int, int]]) -> str:
        lines, buf = [], []
        for i, (u, v) in enumerate(edge_list, 1):
            buf.append(f"{u}-{v}")
            if i % 20 == 0:
                lines.append(" | ".join(buf))
                buf = []
        if buf:
            lines.append(" | ".join(buf))
        return "\n".join(lines)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"### Black Edges (L1 edges) - {len(black_edges)} edges\n")
        f.write(format_edges(black_edges) + "\n\n\n")
        f.write(f"### Red Edges (L2 relationship edges) - {len(red_edges)} edges\n")
        f.write(format_edges(red_edges) + "\n\n\n")
        f.write(f"### Blue Edges (Same L2 code, dotted) - {len(blue_edges)} edges\n")
        f.write(format_edges(blue_edges) + "\n\n\n")

    print(f"[+] edge list written → {out_path}")

# ---------- 経路探索 --------------------------------------------------

def l1_shortest_paths(G: ig.Graph, s: int, t: int, k: int | None) -> list[list[int]]:
    black_eids = [e.index for e in G.es if e["color"] == "black"]
    G_black = G.subgraph_edges(black_eids, delete_vertices=False)

    try:
        all_paths = G_black.get_all_shortest_paths(s, to=t, weights="weight")
        unique_paths = []
        seen = set()
        for path in all_paths:
            tup = tuple(path)
            if tup not in seen:
                unique_paths.append(path)
                seen.add(tup)
            if k and len(unique_paths) >= k:
                break
        return unique_paths
    except:
        return []

def l1l2_paths_nx(G_ig: ig.Graph, allowed: set[int], s: int, t: int, k: int = 5) -> list[list[int]]:
    # igraph → networkx に変換
    G_nx = nx.Graph()
    for v in G_ig.vs:
        if v.index in allowed:
            G_nx.add_node(v.index)

    for e in G_ig.es:
        u, v = e.source, e.target
        if u in allowed and v in allowed:
            G_nx.add_edge(u, v, color=e["color"], weight=e["weight"])

    try:
        gen = nx.shortest_simple_paths(G_nx, s, t, weight="weight")
        paths = []
        for path in gen:
            if any(G_nx[u][v]["color"] in ("red", "blue") for u, v in zip(path, path[1:])):
                paths.append(path)
                if len(paths) >= k:
                    break
        return paths
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []

# ---------- Graphviz 可視化 -----------------------------------------


def render_graph(G: ig.Graph, labels: dict[int, str], s: int, t: int, l1_paths: list[list[int]], out_prefix: str, *, k: int | None = 10) -> None:
    l1_nodes = set(itertools.chain.from_iterable(l1_paths))

    l1e = {tuple(sorted((u, v))) for p in l1_paths for u, v in zip(p, p[1:])}
    l2e = {
        tuple(sorted((e.source, e.target)))
        for e in G.es
        if e["color"] in ("red", "blue")
        and e.source in l1_nodes
        and e.target in l1_nodes
    }

    l1l2 = l1l2_paths_nx(G, l1_nodes, s, t, k)

    gv = graphviz.Graph("L1_vs_L2", engine="dot")
    for n in l1_nodes:
        fill = "green" if n == s else "red" if n == t else "white"
        gv.node(str(n), label=labels.get(n, str(n)), style="filled", fillcolor=fill)

    def add_edges(gv, G: ig.Graph, edge_list: set[tuple[int, int]], *, color: str | None = None, width: str = "2.0") -> None:
        for u, v in edge_list:
            eid = G.get_eid(u, v, error=False)
            if eid == -1:
                continue
            e = G.es[eid]
            col = color if color is not None else (e["color"] if "color" in e.attributes() else "black")
            style = e["style"] if "style" in e.attributes() else ("dotted" if col == "blue" else "solid")
            gv.edge(str(u), str(v), color=col, style=style, penwidth=width)

    def _arrow(col: str) -> str:
        return {"red": "=>", "blue": "--"}.get(col, "->")

    def _path_str(G: ig.Graph, p: list[int]) -> str:
        parts = []
        for u, v in zip(p, p[1:]):
            eid = G.get_eid(u, v, error=False)
            if eid == -1:
                arrow = "??"
            else:
                color = G.es[eid]["color"]
                arrow = {"red": "=>", "blue": "--"}.get(color, "->")
            parts.append(f"{u}{arrow}")
        return "".join(parts) + str(p[-1])
    
    add_edges(gv, G, l1e, color="black", width=PEN_L1)
    add_edges(gv, G, l2e, width=PEN_L2)

    info = [f"L1       {i}: {_path_str(G, p)}" for i, p in enumerate(l1_paths, 1)]
    info += [f"L1+L2    {i}: {_path_str(G, p)}" for i, p in enumerate(l1l2, 1)]
    gv.node("info", label="\n".join(info), shape="plaintext", fontname="Courier")
    gv.edge(str(s), "info", style="invis")

    gv.attr(dpi="300", rankdir="TB", margin="0.3", nodesep="0.3", ranksep="0.3")
    out = f"{out_prefix}/s{s}_g{t}_k{len(l1_paths)}"
    print(f"[+] rendering → {out}.pdf")
    gv.render(out, format="pdf", cleanup=True, quiet=True)
    try:
        gv.view()
    except:
        pass
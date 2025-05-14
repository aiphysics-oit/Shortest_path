#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shortest_path.py   –  L1 最短経路 ⇒ L2 エッジ追加 (比較用プログラム準拠)

* build_graph() は、質問者さんが提示した Python スニペットと
  **同じロジック** でエッジを生成します。
* 青＝weight 0, dotted  ；赤＝weight 1 ；黒＝weight 1
"""

from __future__ import annotations
import argparse, itertools, sys
from pathlib import Path
import graphviz, networkx as nx

# ---------- 重み & 描画パラメータ -------------------------------
W_BLACK = 1.0        # L1
W_RED   = 1.0        # L2
W_BLUE  = 0.5       # 同一 L2

PEN_L1    = "3.0"    # L1 最短を強調する線幅
PEN_L2    = "2.0"    # L2 追加エッジ

# ---------- CLI ------------------------------------------------
def cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("-s", "--start", type=int, default=0)
    p.add_argument("-g", "--goal",  type=int, default=25)
    p.add_argument("-k", "--k_paths", type=int, default=10,
                   help="列挙する L1 最短経路本数 (0=制限なし)")
    return p.parse_args()

# ---------- build_graph()  ← 比較用と同じロジック --------------
def build_graph() -> tuple[nx.Graph, dict[int, str], dict[int, str]]:
    G = nx.Graph()

    root = Path(__file__).resolve().parent
    l1_path = root / "1050400_L1-L2_DB.txt"
    l2_path = root / "1050400_L2_DB.txt"

    # ===== L1‑L2 ファイル ======================================
    lines = l1_path.read_text(encoding="utf-8").splitlines()
    n_nodes = int(lines[0].split()[0])

    node_labels: dict[int, str] = {}
    L2code_to_L1num: dict[str, list[int]] = {}
    L1num_to_L2code: dict[int, str] = {}

    # --- ノード -------------------------------------------------
    for ln in lines[1 : 1 + n_nodes]:
        nid = int(ln.split()[0])

        L1s = ln.find("L1  |") + len("L1  |")
        L1e = ln.find("L2")
        l1_label = ln[L1s:L1e].strip().replace("|", "\n")

        L2s = ln.find("L2  |") + len("L2  |")
        L2e = ln.find("#", L2s)
        l2_label = ln[L2s:L2e].strip()

        label = f"# {nid}\n{l1_label}\n{l2_label}"
        G.add_node(nid, label=label)
        node_labels[nid] = label

        L2code_to_L1num.setdefault(l2_label, []).append(nid)
        L1num_to_L2code[nid] = l2_label

    print("1")

    # --- 黒エッジ (L1) -----------------------------------------
    idx_edges = next(i + 1 for i, ln in enumerate(lines)
                     if "# number of l1 edges" in ln.lower())
    for ln in lines[idx_edges:]:
        sp = ln.split()
        if len(sp) < 2 or not sp[0].isdigit():
            continue
        u, v = map(int, sp[:2])
        G.add_edge(u, v, color="black", weight=W_BLACK)
    print("B")

    # ===== L2 ファイル =========================================
    lines = l2_path.read_text(encoding="utf-8").splitlines()
    n_l2_nodes = int(lines[0].split()[0])

    # L2 番号 ↔︎ ラベル
    L2num_to_code: dict[int, str] = {}
    for ln in lines[1 : 1 + n_l2_nodes]:
        idx = ln.find("encode_level: 2 |") + len("encode_level: 2 |")
        label = ln[idx : ln.find("Connected", idx)].strip()
        L2num_to_code[int(ln.split()[0])] = label

    idx_edges = next(i + 1 for i, ln in enumerate(lines)
                     if "# number of l2 edges" in ln.lower())
    for ln in lines[idx_edges:]:
        sp = ln.split()
        if len(sp) < 2 or not sp[0].isdigit():
            continue
        a, b = map(int, sp[:2])
        lab_a = L2num_to_code.get(a)
        lab_b = L2num_to_code.get(b)
        if lab_a is None or lab_b is None:
            continue

        for u in L2code_to_L1num.get(lab_a, []):
            for v in L2code_to_L1num.get(lab_b, []):
                if u == v or G.has_edge(u, v):
                    continue
                G.add_edge(u, v, color="red", weight=W_RED)   # 赤エッジ
    print("R")

    # ===== 青点線 (同一 L2 ラベル) =============================
    for u in G.nodes():
        for v in G.nodes():
            if u >= v:
                continue
            if L1num_to_L2code[u] == L1num_to_L2code[v] and not G.has_edge(u, v):
                G.add_edge(u, v, color="blue", weight=W_BLUE, style="dotted")

    print("B")

    return G, node_labels, L1num_to_L2code

def write_edge_lists(G: nx.Graph, out_path: str = "all_edges.txt") -> None:
    """グラフ G から色別エッジ一覧を out_path に保存"""

    black_edges, red_edges, blue_edges = [], [], []
    for u, v, data in G.edges(data=True):
        col = data.get("color", "")
        if col == "black":
            black_edges.append((u, v))
        elif col == "red":
            red_edges.append((u, v))
        elif col == "blue":
            blue_edges.append((u, v))

    def format_edges(edge_list: list[tuple[int, int]]) -> str:
        """20 組ごとに改行し ‘|’ 区切りで整形"""
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

# ---------- 経路探索 -------------------------------------------
def l1_shortest_paths(G: nx.Graph, s: int, t: int, k: int | None) -> list[list[int]]:
    H = nx.Graph((u, v, d) for u, v, d in G.edges(data=True) if d["color"] == "black")
    gen = nx.all_shortest_paths(H, s, t, weight="weight")
    return list(itertools.islice(gen, k)) if k else list(gen)

def l1l2_paths(G: nx.Graph, allowed: set[int], s: int, t: int,
               k: int | None = 5) -> list[list[int]]:
    SG = G.subgraph(allowed)
    gen = nx.shortest_simple_paths(SG, s, t, weight="weight")
    paths: list[list[int]] = []
    for p in gen:
        if any(SG[u][v]["color"] in ("red", "blue") for u, v in zip(p, p[1:])):
            paths.append(p)
            if k and len(paths) >= k:
                break
    return paths

# ---------- 可視化ユーティリティ -------------------------------
def arrow(col: str) -> str:
    return {"red": "=>", "blue": "--"}.get(col, "->")

def path_str(G: nx.Graph, p: list[int]) -> str:
    return "".join(f"{u}{arrow(G[u][v]['color'])}" for u, v in zip(p, p[1:])) + str(p[-1])

def add_edges(gv: graphviz.Graph, G: nx.Graph, edges: set[tuple[int, int]],
              *, color: str | None = None, width: str = "2.0"):
    for u, v in edges:
        d = G[u][v]
        if color is not None:
            d["color"] = color
        gv.edge(str(u), str(v),
                color=d["color"],
                penwidth=width,
                style=d.get("style", "dotted" if d["color"] == "blue" else "solid"))

# ---------- メイン ---------------------------------------------
def main() -> None:
    args = cli()
    s, t = args.start, args.goal
    k    = args.k_paths if args.k_paths > 0 else None

    G, labels, _ = build_graph()

    write_edge_lists(G, "all_edges.txt")


    # ① L1 最短経路
    l1_paths = l1_shortest_paths(G, s, t, k)
    l1_nodes = set(itertools.chain.from_iterable(l1_paths))

    # ② L2 / blue エッジ（allowed 内）
    l2_edges = {tuple(sorted((u, v)))
                for u, v, d in G.edges(data=True)
                if d["color"] in ("red", "blue") and u in l1_nodes and v in l1_nodes}

    # ---------- Graphviz 描画 ---------------------------------
    gv = graphviz.Graph("L1_vs_L2", engine="dot")

    for n in l1_nodes:
        fill = "green" if n == s else "red" if n == t else "white"
        gv.node(str(n), label=labels[n], style="filled", fillcolor=fill)

    # L1 最短経路 (紫で上書き表現)
    l1e = {tuple(sorted((u, v))) for p in l1_paths for u, v in zip(p, p[1:])}
    add_edges(gv, G, l1e, color="black", width=PEN_L1)

    # 追加された赤・青エッジ
    add_edges(gv, G, l2_edges, width=PEN_L2)

    # L1+L2 経路
    l1l2 = l1l2_paths(G, l1_nodes, s, t, k)

    # 情報ノード
    info  = [f"L1   {i}: {path_str(G, p)}" for i, p in enumerate(l1_paths, 1)]
    info += [f"L1+L2    {i}: {path_str(G, p)}" for i, p in enumerate(l1l2,   1)]
    gv.node("info", label="\n".join(info), shape="plaintext", fontname="Courier")
    gv.edge(str(s), "info", style="invis")

    gv.attr(dpi="300", rankdir="TB", margin="0.3", nodesep="0.3", ranksep="0.3")
    out = "l1_l2_comparison_final"
    print(f"[+] rendering → {out}.pdf")
    gv.render(out, format="pdf", cleanup=True, quiet=True)
    gv.view()


# --------------------------------------------------------------
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nInterrupted by user")

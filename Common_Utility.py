from __future__ import annotations
import itertools, re, pickle, subprocess, sys
from pathlib import Path
import networkx as nx
import graphviz

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


def build_graph(l1l2_path: Path, l2_path: Path) -> tuple[nx.Graph, dict[int,str], dict[int,str]]:
    """元コードと同等のロジックで NetworkX グラフを生成"""
    G = nx.Graph()

    # ===== L1-L2 ファイル =============================================
    lines = l1l2_path.read_text(encoding="utf-8").splitlines()
    n_nodes = int(lines[0].split()[0])

    node_labels: dict[int,str] = {}
    L2code_to_L1num: dict[str,list[int]] = {}
    L1num_to_L2code: dict[int,str] = {}

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

    idx_edges = next(i+1 for i,ln in enumerate(lines) if "# number of l1 edges" in ln.lower())
    for ln in lines[idx_edges:]:
        sp = ln.split()
        if len(sp) < 2 or not sp[0].isdigit():
            continue
        u, v = map(int, sp[:2])
        G.add_edge(u, v, color="black", weight=W_BLACK)
    
    print("black")

    # ===== L2 ファイル ================================================
    lines = l2_path.read_text(encoding="utf-8").splitlines()
    n_l2_nodes = int(lines[0].split()[0])
    L2num_to_code: dict[int,str] = {}
    for ln in lines[1 : 1+n_l2_nodes]:
        idx = ln.find("encode_level: 2 |") + len("encode_level: 2 |")
        label = ln[idx: ln.find("Connected", idx)].strip()
        L2num_to_code[int(ln.split()[0])] = label

    idx_edges = next(i+1 for i,ln in enumerate(lines) if "# number of l2 edges" in ln.lower())
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
                G.add_edge(u, v, color="red", weight=W_RED)
    print("red")

    # ===== 青点線 (同一 L2) ===========================================
    for u in G.nodes():
        for v in G.nodes():
            if u >= v:
                continue
            if L1num_to_L2code[u] == L1num_to_L2code[v] and not G.has_edge(u,v):
                G.add_edge(u, v, color="blue", weight=W_BLUE, style="dotted")

    print("blue")

    return G, node_labels, L1num_to_L2code

# ---------- 経路探索 --------------------------------------------------

def l1_shortest_paths(G: nx.Graph, s: int, t: int, k: int | None) -> list[list[int]]:
    H = nx.Graph((u,v,d) for u,v,d in G.edges(data=True) if d["color"] == "black")
    gen = nx.all_shortest_paths(H, s, t, weight="weight")
    return list(itertools.islice(gen, k)) if k else list(gen)


def l1l2_paths(G: nx.Graph, allowed: set[int], s: int, t: int, k: int | None=5) -> list[list[int]]:
    SG = G.subgraph(allowed)
    gen = nx.shortest_simple_paths(SG, s, t, weight="weight")
    paths: list[list[int]] = []
    for p in gen:
        if any(SG[u][v]["color"] in ("red","blue") for u,v in zip(p,p[1:])):
            paths.append(p)
            if k and len(paths) >= k:
                break
    return paths

# ---------- Graphviz 可視化 -----------------------------------------

def _arrow(col:str) -> str:
    return {"red":"=>", "blue":"--"}.get(col, "->")

def _path_str(G:nx.Graph, p:list[int]) -> str:
    return "".join(f"{u}{_arrow(G[u][v]['color'])}" for u,v in zip(p,p[1:])) + str(p[-1])

def _add_edges(gv: graphviz.Graph, G:nx.Graph, edges:set[tuple[int,int]], *, color:str|None=None, width:str="2.0") -> None:
    for u,v in edges:
        d = G[u][v]
        if color is not None:
            d["color"] = color
        gv.edge(str(u), str(v), color=d["color"], penwidth=width, style=d.get("style","dotted" if d["color"]=="blue" else "solid"))


def render_graph(G:nx.Graph, labels:dict[int,str], s:int, t:int, l1_paths:list[list[int]], out_prefix:str, *, k:int|None=10) -> None:
    """Graphviz PDF を生成して開く"""
    l1_nodes = set(itertools.chain.from_iterable(l1_paths))
    l2_edges = {tuple(sorted((u,v))) for u,v,d in G.edges(data=True) if d["color"] in ("red","blue") and u in l1_nodes and v in l1_nodes}
    l1e = {tuple(sorted((u,v))) for p in l1_paths for u,v in zip(p,p[1:])}

    l1l2 = l1l2_paths(G, l1_nodes, s, t, k)

    gv = graphviz.Graph("L1_vs_L2", engine="dot")
    for n in l1_nodes:
        fill = "green" if n==s else "red" if n==t else "white"
        gv.node(str(n), label=labels[n], style="filled", fillcolor=fill)
    _add_edges(gv, G, l1e, color="black", width=PEN_L1)
    _add_edges(gv, G, l2_edges, width=PEN_L2)

    info  = [f"L1       {i}: {_path_str(G, p)}" for i,p in enumerate(l1_paths,1)]
    info += [f"L1+L2    {i}: {_path_str(G, p)}" for i,p in enumerate(l1l2,1)]
    gv.node("info", label="\n".join(info), shape="plaintext", fontname="Courier")
    gv.edge(str(s), "info", style="invis")

    gv.attr(dpi="300", rankdir="TB", margin="0.3", nodesep="0.3", ranksep="0.3")
    out = f"{out_prefix}_l1_l2_comparison"
    print(f"[+] rendering → {out}.pdf")
    gv.render(out, format="pdf", cleanup=True, quiet=True)
    try:
        gv.view()
    except Exception:
        pass
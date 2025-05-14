from __future__ import annotations
import argparse, pickle, subprocess, sys
from pathlib import Path
from shortest_path_base import l1_shortest_paths, render_graph, auto_prefix

# ---------- CLI -------------------------------------------------------
def cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Shortest‑path solver using cached graph.")
    p.add_argument("--l1l2", default="1020000_L1-L2_DB.txt", help="L1-L2 DB file path")
    p.add_argument("--l2",   default="1020000_L2_DB.txt",    help="L2 DB file path")
    p.add_argument("-c", "--cache", default=None, help="Pickle cache file (default: auto)")
    p.add_argument("-s", "--start", type=int, default=0)
    p.add_argument("-g", "--goal",  type=int, default=25)
    p.add_argument("-k", "--k_paths", type=int, default=10)
    p.add_argument("--no-view", action="store_true", help="Do not open PDF viewer")
    return p.parse_args()

# ---------- main ------------------------------------------------------

def main():
    args = cli()
    l1l2_path = Path(args.l1l2).expanduser().resolve()
    l2_path   = Path(args.l2).expanduser().resolve()

    if args.cache is None:
        args.cache = f"{auto_prefix(l1l2_path)}_graph.pkl"
    cache_path = Path(args.cache).expanduser().resolve()

    # --- キャッシュが無ければ自動生成 ------------------------------
    if not cache_path.exists():
        print(f"[i] Cache {cache_path.name} not found. Building…")
        subprocess.run([sys.executable, "build_graph_.py", "--l1l2", str(l1l2_path), "--l2", str(l2_path), "--cache", str(cache_path)], check=True)

    # --- 読込 --------------------------------------------------------
    with cache_path.open("rb") as f:
        G, node_labels, L1num_to_L2code = pickle.load(f)
    print(f"[✓] Cache loaded (|V|={G.number_of_nodes()}, |E|={G.number_of_edges()})")

    # --- 経路探索 ----------------------------------------------------
    k = args.k_paths if args.k_paths > 0 else None
    paths = l1_shortest_paths(G, args.start, args.goal, k)



    # --- Graphviz 描画 ---------------------------------------------
    out_prefix = auto_prefix(l1l2_path)
    render_graph(G, node_labels, args.start, args.goal, paths, out_prefix, k=k)
    if args.no_view:
        print("[i] PDF rendered (viewer suppressed by --no-view)")

if __name__ == "__main__":
    main()
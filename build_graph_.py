from __future__ import annotations
import argparse, pickle
from pathlib import Path
from shortest_path_base import build_graph, auto_prefix


def cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build NetworkX graph and cache it as Pickle.")
    p.add_argument("--l1l2", default="1050400_L1-L2_DB.txt", help="L1-L2 DB file path")
    p.add_argument("--l2",   default="1050400_L2_DB.txt",    help="L2 DB file path")
    p.add_argument("-c", "--cache", default=None, help="Pickle cache file path (default: auto)")
    p.add_argument("-f", "--force", action="store_true", help="Rebuild even if cache exists")
    return p.parse_args()


def main():
    args = cli()

    l1l2_path = Path(args.l1l2).expanduser().resolve()
    l2_path   = Path(args.l2).expanduser().resolve()

    # --- default cache name -----------------------------------------
    if args.cache is None:
        args.cache = f"{auto_prefix(l1l2_path)}_graph.pkl"
    cache_path = Path(args.cache).expanduser().resolve()

    if cache_path.exists() and not args.force:
        print(f"[✓] Cache already exists → {cache_path.name} (use --force to rebuild)")
        return

    G, node_labels, L1num_to_L2code = build_graph(l1l2_path, l2_path)

    with cache_path.open("wb") as f:
        pickle.dump((G, node_labels, L1num_to_L2code), f)
    print(f"[+] Graph cached to {cache_path.relative_to(Path.cwd())}")

if __name__ == "__main__":
    main()
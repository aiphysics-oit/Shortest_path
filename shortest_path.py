import networkx as nx
import graphviz

# ==== データ読み込み ====
G = nx.Graph()
node_labels = {}
l2_labels = {}

with open('ROBOT_DB_L1-L2.txt', 'r') as file:
    lines = file.readlines()

num_nodes = int(lines[0].split()[0])
node_data_lines = lines[1:num_nodes + 1]

for line in node_data_lines:
    node_id = int(line.split()[0])
    L1start = line.find('L1  |') + len('L1  |')
    L1end = line.find('L2')
    L1label = line[L1start:L1end].strip().replace('|', '\n')
    L2start = line.find('L2  |') + len('L2  |')
    L2end = line.find('#')
    L2label = line[L2start:L2end].strip()
    label = f"# {node_id}\n{L1label}\n{L2label}"
    G.add_node(node_id, label=label)
    node_labels[node_id] = label
    l2_labels[node_id] = L2label

# ==== L1エッジ ====
for i, line in enumerate(lines):
    if '# number of L1 edges'.lower() in line.strip().lower():
        edge_start_idx = i + 1
        break

for line in lines[edge_start_idx:]:
    parts = line.split()
    if len(parts) >= 2:
        u, v = int(parts[0]), int(parts[1])
        G.add_edge(u, v, color='black', weight=1)

# ==== L2エッジ ====
with open('ROBOT_DB_L2.txt', 'r') as file:
    lines = file.readlines()

for i, line in enumerate(lines):
    if '# number of L2 edges'.lower() in line.strip().lower():
        edge_start_idx = i + 1
        break

for line in lines[edge_start_idx:]:
    parts = line.split()
    if len(parts) >= 2:
        u, v = int(parts[0]), int(parts[1])
        G.add_edge(u, v, color='red', weight=1)

# L2ラベルが一致するものは青に変更
for u, v in G.edges():
    if G[u][v]['color'] == 'red' and l2_labels.get(u) == l2_labels.get(v):
        G[u][v]['color'] = 'blue'

# ==== L1グラフ構築 ====
G_L1 = nx.Graph()
for u, v, d in G.edges(data=True):
    if d['color'] == 'black':
        G_L1.add_edge(u, v)

# ==== スタート・ゴール指定 ====
start = 0
goal = 25

try:
    all_l1_paths = list(nx.all_shortest_paths(G_L1, source=start, target=goal))
except nx.NetworkXNoPath:
    all_l1_paths = []

# ==== 描画準備 ====
G_gv = graphviz.Graph('l1_l2_comparison', engine='dot')
involved_nodes = set()
involved_edges = set()
path_descriptions = []

def describe_path(path, G):
    desc = []
    for u, v in zip(path, path[1:]):
        edge_data = G.get_edge_data(u, v, {})
        connector = '--' if edge_data.get('color') == 'blue' else '->'
        desc.append(str(u))
        desc.append(connector)
    desc.append(str(path[-1]))
    return ''.join(desc)

# ==== パスごとの処理 ====
for idx, l1_path in enumerate(all_l1_paths):
    path_num = idx + 1
    l1_nodes = set(l1_path)

    # --- L2補完探索用グラフ（L1ノード集合 + L1/L2エッジ） ---
    G_sub = nx.Graph()
    G_sub.add_nodes_from(l1_nodes)
    for u in l1_nodes:
        for v in l1_nodes:
            if u != v and G.has_edge(u, v):
                if G[u][v]['color'] in ('red', 'blue'):
                    print(f"L2補完エッジ: {u} -- {v}, 色: {G[u][v]['color']}")

    # --- L2経路探索 ---
    try:
        l2_path = nx.shortest_path(G_sub, source=start, target=goal)
    except nx.NetworkXNoPath:
        l2_path = None

    # === パス表示 ===
    path_descriptions.append(f"Path {path_num} (L1): {describe_path(l1_path, G)}")
    if l2_path is None:
        path_descriptions.append(f"Path {path_num} (L2): No path available.")
    elif l2_path != l1_path:
        path_descriptions.append(f"Path {path_num} (L2): {describe_path(l2_path, G)}")
    # 同じなら省略

    # === ノード・エッジ収集 ===
    involved_nodes.update(l1_path)
    if l2_path:
        involved_nodes.update(l2_path)

    for u, v in zip(l1_path, l1_path[1:]):
        involved_edges.add((u, v, 'l1'))
    if l2_path:
        for u, v in zip(l2_path, l2_path[1:]):
            if (u, v, 'l1') not in involved_edges and (v, u, 'l1') not in involved_edges:
                involved_edges.add((u, v, 'l2'))

# ==== ノード描画 ====
for node in involved_nodes:
    label = node_labels.get(node, "")
    fill = 'green' if node == start else 'red' if node == goal else 'white'
    G_gv.node(
        str(node), label=label,
        style='filled', fillcolor=fill,
        fontsize='10', fontname='Helvetica',
        fixedsize='false'
    )

# ==== エッジ描画 ====
for u, v, path_type in involved_edges:
    data = G.get_edge_data(u, v) or G.get_edge_data(v, u) or {}
    color = data.get('color', 'black')
    if path_type == 'l1':
        G_gv.edge(str(u), str(v), color='purple', penwidth='3.0', style='solid')
    else:
        style = 'dashed' if color == 'blue' else 'solid'
        G_gv.edge(str(u), str(v), color=color, penwidth='3.0', style=style)

# ==== 経路表示ノード ====
path_label = '\n'.join(path_descriptions)
G_gv.node('path_explain', label=path_label, shape='plaintext',
          fontsize='16', fontname='Courier', width='3')
G_gv.edge(str(start), 'path_explain', style='invis', weight='100')

# ==== グラフ属性 ====
G_gv.attr(
    rankdir='TB',
    dpi='300',
    margin='0.3',
    nodesep='0.3',
    ranksep='0.3',
    splines='true',
    overlap='false'
)

# ==== 出力 ====
file_name = 'l1_l2_comparison_final'
G_gv.render(file_name, format='pdf', cleanup=True)
G_gv.view()

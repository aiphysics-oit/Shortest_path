import networkx as nx
import graphviz

# ==== データ読み込み ====
G = nx.Graph()

# L1-L2ファイルの読み込み
with open("ROBOT_DB_L1-L2.txt", 'r') as file:
    lines = file.readlines()

# ノード数の取得
L1_L2_nodes = int(lines[0].split()[0])
# ノードラベル辞書を作成
node_labels = {}
L2code_to_L1num = {}
L1num_to_L2code = {}

# エッジを保存するためのセット
black_edges = set()
red_edges = set()
blue_edges = set()

# L1-L2ファイルからノード情報を取得
node_data_lines = lines[1:L1_L2_nodes + 1]
for line in node_data_lines:
    parts = line.split()
    node_id = int(parts[0])

    # L1およびL2ラベルの抽出
    L1start = line.find('L1  |') + len('L1  |')
    L1end = line.find('L2')
    L1label = line[L1start:L1end].strip().replace('|', '\n')

    L2start = line.find('L2  |') + len('L2  |')
    L2end = line.find('#')
    L2label = line[L2start:L2end].strip()

    # ノードラベルを作成し、ノードを追加
    label = f"{L1label}\n"
    G.add_node(node_id, label=label)
    node_labels[node_id] = label

    # L1ノードとL2ラベルの対応関係を保存
    if L2label not in L2code_to_L1num:
        L2code_to_L1num[L2label] = []
    L2code_to_L1num[L2label].append(node_id)
    L1num_to_L2code[node_id] = L2label

# 黒いエッジの追加
edge_start_idx = None
for i, line in enumerate(lines):
    if '# number of L1 edges'.lower() in line.strip().lower():
        edge_start_idx = i + 1
        break

for line in lines[edge_start_idx:]:
    parts = line.split()
    if len(parts) < 2:
        continue
    try:
        node1 = int(parts[0])
        node2 = int(parts[1])
    except ValueError:
        continue
    black_edges.add((node1, node2))

# L2ファイルの読み込み
with open("ROBOT_DB_L2.txt", 'r') as file:
    lines = file.readlines()

L2_nodes = int(lines[0].split()[0])
L2num_to_L2code = {}
L2code_to_L2num = {}

L2_node_data_lines = lines[1:L2_nodes + 1]
for line in L2_node_data_lines:
    parts = line.split()
    node_id = int(parts[0])

    start = line.find('encode_level: 2 |') + len('encode_level: 2 |')
    end = line.find('Connected')
    Label = line[start:end].strip()
    L2num_to_L2code[node_id] = Label
    L2code_to_L2num[Label] = node_id
    label = label + f"#{node_id}"

# 赤いエッジの追加
edge_start_idx = None
for i, line in enumerate(lines):
    if '# number of L2 edges'.lower() in line.strip().lower():
        edge_start_idx = i + 1
        break

for line in lines[edge_start_idx:]:
    parts = line.split()
    if len(parts) < 2:
        continue
    try:
        l2_node1 = int(parts[0])
        l2_node2 = int(parts[1])
    except ValueError:
        continue

    if l2_node1 in L2num_to_L2code and l2_node2 in L2num_to_L2code:
        l2_label1 = L2num_to_L2code[l2_node1]
        l2_label2 = L2num_to_L2code[l2_node2]

        if l2_label1 in L2code_to_L1num and l2_label2 in L2code_to_L1num:
            for l1_node1 in L2code_to_L1num[l2_label1]:
                for l1_node2 in L2code_to_L1num[l2_label2]:
                    if not (l1_node1, l1_node2) in black_edges:
                        red_edges.add((l1_node1, l1_node2))

# 青いエッジの追加
for l2_label, node_list in L2code_to_L1num.items():
    for i in range(len(node_list)):
        for j in range(i + 1, len(node_list)):
            id_1 = node_list[i]
            id_2 = node_list[j]
            blue_edges.add((id_1, id_2))

for edge in red_edges:
    if edge not in black_edges:
        G.add_edge(edge[0], edge[1], color='red', weight=1)

for edge in black_edges:
    G.add_edge(edge[0], edge[1], color='black', weight=1)

for edge in blue_edges:
    if not G.has_edge(edge[0], edge[1]):  # 他のエッジが存在しない場合のみ追加
        G.add_edge(edge[0], edge[1], color='blue', weight=0, style='dotted')  # 青い点線を追加

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

    # --- L2エッジのみの補完グラフ ---
    G_sub_l2_only = nx.Graph()
    G_sub_l2_only.add_nodes_from(l1_nodes)
    for u in l1_nodes:
        for v in l1_nodes:
            if u != v and G.has_edge(u, v):
                if G[u][v]['color'] in ('red', 'blue'):
                    G_sub_l2_only.add_edge(u, v, **G[u][v])

    # --- L2経路探索 ---
    try:
        l2_path = nx.shortest_path(G_sub_l2_only, source=start, target=goal)
    except nx.NetworkXNoPath:
        l2_path = None

    # === パス表示 ===
    path_descriptions.append(f"Path {path_num} (L1): {describe_path(l1_path, G)}")
    if l2_path is None:
        path_descriptions.append(f"Path {path_num} (L2): No path available.")
    elif l2_path != l1_path:
        path_descriptions.append(f"Path {path_num} (L2): {describe_path(l2_path, G)}")

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

# ==== 経路説明ノード ====
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

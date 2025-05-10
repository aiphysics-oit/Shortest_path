G = nx.Graph()

# ファイルの読み込み（仮定的なファイル名）
with open('ROBOT_DB_L1-L2.txt', 'r') as file:
    lines = file.readlines()

# ノード数の取得
L1_L2_nodes = int(lines[0].split()[0])

# ノードラベルとL2ラベル用の辞書を用意
node_labels = {}
l2_labels = {}
L2code_to_L1num = {}
L1num_to_L2code = {}

# ノード情報の読み込み
node_data_lines = lines[1:L1_L2_nodes + 1]
for line in node_data_lines:
    parts = line.split()
    node_id = int(parts[0])

    # L1ラベルの取得
    L1start = line.find('L1  |') + len('L1  |')
    L1end = line.find('L2')
    L1label = line[L1start:L1end].strip()
    L1label = L1label.replace('|', '\n')

    # L2ラベルの取得
    L2start = line.find('L2  |') + len('L2  |')
    L2end = line.find('#')
    L2label = line[L2start:L2end].strip()

    # ノードラベルの作成
    label = f"# {node_id}\n{L1label}\n{L2label}"
    G.add_node(node_id, label=label)
    node_labels[node_id] = label  # L1ラベルだけでなく、完全なラベルを保存
    # L2ラベルも保存
    L1num_to_L2code[node_id] = L2label 
    if L2label not in L2code_to_L1num:
        L2code_to_L1num[L2label] = []  # Initialize the list if it's not present
    L2code_to_L1num[L2label].append(node_id)
#     file_name = "debag.txt"
#     with open(file_name, "w") as file:
#         file.write("L1num_to_L2code:\n")
#         for key, value in L1num_to_L2code.items():
#             file.write(f"{key}: {value}\n")

#         file.write("\nL2code_to_L1num:\n")
#         for key, value in L2code_to_L1num.items():
#             file.write(f"{key}: {value}\n")

# return

# L1エッジの読み込み
edge_start_idx = None
for i, line in enumerate(lines):
    if '# number of L1 edges'.lower() in line.strip().lower():
        edge_start_idx = i + 1
        break

# L1エッジの追加（同じL2ラベルなら青線、それ以外は黒線）
for line in lines[edge_start_idx:]:
    parts = line.split()
    if len(parts) < 2:
        continue

    try:
        node1 = int(parts[0])
        node2 = int(parts[1])
    except ValueError:
        continue

    G.add_edge(node1, node2, color='black', weight=1)  # L1エッジは黒線

# L2エッジの追加（赤線） - 元のコードに基づく
with open('ROBOT_DB_L2.txt', 'r') as file:
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
    
edge_start_idx = None
for i, line in enumerate(lines):
    if '# number of L2 edges'.lower() in line.strip().lower():
        edge_start_idx = i + 1
        break

# 実際に存在するL2エッジを読み込む
actual_l2_edges = set()
for line in lines[edge_start_idx:]:
    parts = line.split()
    if len(parts) < 2:
        continue

    try:
        l2_node0 = int(parts[0])
        l2_node1 = int(parts[1])

    except ValueError:
        continue

    for L2line0 in L1num_to_L2code[node_id]:
        if l2_node0 in L2num_to_L2code and L2line0 in L1num_to_L2code and L1num_to_L2code[L2line0] == L2num_to_L2code[l2_node0]:
            for L2line1 in L1num_to_L2code[node_id]:
                if l2_node1 in L2num_to_L2code and L2line1 in L1num_to_L2code and L1num_to_L2code[L2line1] == L2num_to_L2code[l2_node1]:
                    for i in L2code_to_L1num[L2line0]:
                        for j in L2code_to_L1num[L2line1]:
                            G.add_edge(L2code_to_L1num[L2line0][i], L2code_to_L1num[L2line1][j], color='red', weight=1)  # L2エッジは赤線
                            actual_l2_edges.add((L2code_to_L1num[L2line0][i], L2code_to_L1num[L2line1][j]))
                            print(f"Added edge between {L2code_to_L1num[L2line0][i]} and {L2code_to_L1num[L2line1][j]} (red edge)")


# L2ラベルが同じでも、実際にL2エッジファイルに存在しないエッジは追加しないように修正
for node1 in G.nodes():
    for node2 in G.nodes():
        if node1 != node2 and l2_labels.get(node1) == l2_labels.get(node2):
            if not G.has_edge(node1, node2) and (node1, node2) in actual_l2_edges:
                G.add_edge(node1, node2, color='blue', weight=0)
            elif G.has_edge(node1, node2) and (node1, node2) in actual_l2_edges:
                G[node1][node2]['color'] = 'blue'

# 1点目: L1エッジのみを考慮した最短経路を計算
start = 31
goal = 475

# L1エッジのみの最短経路を計算
L1_only_edges = [(u, v) for u, v, data in G.edges(data=True) if data['color'] == 'black']
L1_only_G = nx.Graph()
L1_only_G.add_edges_from(L1_only_edges)

# L1エッジのみの全最短経路を計算
all_shortest_paths_L1 = list(nx.all_shortest_paths(L1_only_G, source=start, target=goal, weight='weight'))
l1_path = all_shortest_paths_L1[0] if all_shortest_paths_L1 else None
all_shortest_paths_full = list(nx.all_shortest_paths(G, source=start, target=goal, weight='weight'))

# 最短経路に関連するノードとエッジのみを描画
G_gv = graphviz.Graph('comparison_all_shortest_paths', engine='dot')

# ノードの追加（始点を緑、終点を赤にする）
all_nodes = set()
for paths in all_shortest_paths_L1 + all_shortest_paths_full:
    all_nodes.update(paths)

node_paths = {}

# 各経路でノードがどの経路に含まれているかを追跡
for idx, path in enumerate(all_shortest_paths_full):
    path_number = idx + 1  # 経路番号を1からスタート
    for node in path:
        if node not in node_paths:
            node_paths[node] = []
        node_paths[node].append(path_number)

# L1経路のみでノードラベルを非表示にする
if all_shortest_paths_L1:  # L1経路が存在する場合
    for l1_path in all_shortest_paths_L1:
        path_edges_L1 = list(zip(l1_path, l1_path[1:]))
        for node1, node2 in path_edges_L1:
            G_gv.edge(str(node1), str(node2), color='purple', penwidth='5.0', style='solid')  # 紫色で描画

        # L1経路のノードにラベルを表示しない
        for node in l1_path:
            G_gv.node(str(node), label="")  # L1経路のノードラベルを空に設定

# L1＋L2の経路でノードラベルとパス番号を表示
for node in all_nodes:
    if not node_paths.get(node):  # ノードが含まれる経路がない場合はスキップ
        continue

    label = node_labels.get(node, "")  # 既存のラベルを取得
    path_numbers = ', '.join(map(str, node_paths[node]))  # 経路番号をカンマ区切りで取得

    if node == start:
        G_gv.node(str(node), label=f"{label}\nPaths: {path_numbers}", style='filled', fillcolor='green')
    elif node == goal:
        G_gv.node(str(node), label=f"{label}\nPaths: {path_numbers}", style='filled', fillcolor='red')
    else:
        G_gv.node(str(node), label=f"{label}\nPaths: {path_numbers}")  # L1＋L2経路のみノード情報を表示


# L1 + L2エッジを含むすべての最短経路（赤太線で描画）
for idx, path in enumerate(all_shortest_paths_full):
    path_edges_full = list(zip(path, path[1:]))
    penwidth = 2 + idx  # Increase penwidth for each path
    for node1, node2 in path_edges_full:
        if (node1, node2) not in path_edges_L1:  # Avoid overlap with L1 edges
            edge_color = G[node1][node2]['color']
            edge_style = 'dashed' if edge_color in ['blue'] else 'solid'
            G_gv.edge(str(node1), str(node2), color=edge_color, penwidth=str(penwidth), style=edge_style)

            
# L1経路を紫色で表示するための変更
for idx, path in enumerate(all_shortest_paths_full):
    # 経路のノードを ' -> ' で繋げる部分を改行に変更して縦に表示
    path_str = ' -> '.join(map(str, path)).replace(' -> ', '\n')  # 改行で経路を表示
    G_gv.node(f'Path{idx + 1}', label=f"Path {idx + 1}:\n{path_str}", shape='plaintext')


# グラフの属性を設定してレンダリング
G_gv.attr(rankdir='TB')
G_gv.attr(size='700,150!', dpi='300', margin='0.5')
G_gv.attr(splines='true')
G_gv.attr(overlap='false')
G_gv.render(f'graphviz_comparison_shortest_paths', format='svg', cleanup=True)
G_gv.view()
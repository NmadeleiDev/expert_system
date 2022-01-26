import os
from typing import List
from importlib_metadata import itertools
from consts import * 
from networkx.drawing.nx_pydot import graphviz_layout
import networkx as nx
from matplotlib import pyplot as plt
from networkx import DiGraph


def to_final_answer(answ: int) -> str:
    if answ == ANSWER_TRUE:
        return 'True'
    elif answ == ANSWER_FALSE:
        return 'False'
    elif answ == ANSWER_UNDETERMINED:
        return 'Undetermined'
    else:
        return 'False'

def save_graph_to_file(H, filepath='graph.png'):
    c_dict = {
        '+': 'green',
        '|': 'blue',
        '^': 'pink',
        '!': 'red',
    }

    colors = []
    for n in H:
        col = 'white'
        if H.nodes[n]['type'] == OP_TYPE:
            col = c_dict[H.nodes[n]['op']]
        if H.nodes[n]['type'] == ARG_TYPE and H.nodes[n]['value'] == True:
            col = 'yellow'
        colors.append(col)
        
    pos = graphviz_layout(H, #prog="dot"
    )
    nx.draw(H, pos, with_labels=True, node_color=colors)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')

def root_from(G: nx.DiGraph, node: str):
    pred = node
    while True:
        preds = list(G.predecessors(pred))
        if (len(preds) == 0):
            break
        elif (len(preds) > 1):
            print("WARN: n preds > 1")
            break
        else:
            pred = preds[0]
    return pred

def set_attrs_for_all_edges(G: DiGraph, attr: dict):
    for s, f in G.edges:
        for k, v in attr.items():
            G.edges[s, f][k] = v

def get_zero_indegree_node(G: DiGraph):
    for n, d in G.in_degree():
        if d == 0:
            return n
    print("Err: zero indegree node not found")
    return None

def get_zero_outdegree_node(G: DiGraph):
    for n, d in G.out_degree():
        if d == 0:
            return n
    print("Err: zero indegree node not found")
    return None

def get_node_by_attr(G, attr: tuple):
    for n in G:
        if G[n][attr[0]] == attr[1]:
            return n

def squeeze_implications(G: DiGraph) -> DiGraph:
    Re = DiGraph(G.copy())
    to_remove = []
    for node, t in Re.nodes.data('type'):
        if t == IMPLICATION_TYPE:
            Re.add_edges_from(list(itertools.product(Re.predecessors(node), Re.successors(node))))
            to_remove.append(node)
    for n in to_remove:
        Re.remove_node(n)
    return Re

def check_rules(rules: List[tuple]):
    check = {}
    result = []

    for pre, con in rules:
        s_con = con.lstrip('!')
        val = (len(con) - len(s_con)) % 2 == 0
        if pre not in check.keys():
            check[pre] = {}
        elif pre in check.keys() and s_con in check[pre].keys() and check[pre][s_con] != val:
            print('Rules contradiction: {}=>{} contradicts with {}=>!{}'.format(pre, s_con, pre, s_con))
            print(f'Skipped incorrect rule "{pre}=>{con}"')
            continue
        else:
            check[pre][s_con] = val
        result.append((pre, con))
    return result

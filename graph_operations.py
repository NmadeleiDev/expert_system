from ctypes import Union
from logging import root
import re
from typing import List
import numpy as np
import networkx as nx
from networkx.classes.digraph import DiGraph
from expressions_dict import value_expressions, expr_priority
from consts import *
from classes import *
from utils import *
import os


def build_expr_graph(expr: str) -> DiGraph:
    G = nx.DiGraph()

    arg_regex = re.compile('(\!*\([\(\)\+\!\^\|\w\s]+\)|\!*\w+)')
    operator_regex = re.compile('[\+\|\^]')

    arg_match = arg_regex.findall(expr)
    op_match = operator_regex.findall(re.sub('\(.+\)', '', expr))

    if len(arg_match) != len(op_match) + 1:
        print(f"Error: Expression '{expr}' is invalid, skipping it")
        return G

    parsed_args_roots = []
    for i, raw_arg in enumerate(arg_match):
        without_negs, has_negation = raw_arg.lstrip('!'), False
        if (len(raw_arg) - len(without_negs)) % 2 != 0:
            has_negation = True

        if (without_negs[0] == '(' and without_negs[-1] == ')'):
            subgraph = build_expr_graph(without_negs[1:-1])
        else:
            subgraph = nx.DiGraph()
            subgraph.add_nodes_from([(without_negs, {'type': ARG_TYPE, 'label': without_negs, 'value': False})])

        if has_negation:
            prev_root = get_zero_indegree_node(subgraph)
            subgraph.add_nodes_from([(raw_arg, {'type': OP_TYPE, 'op': '!', 'args': [prev_root]})])
            subgraph.add_edge(raw_arg, prev_root)

        parsed_args_roots.append(get_zero_indegree_node(subgraph))
        G.update(subgraph)

    for op, idx in sorted([(o, i) for i, o in enumerate(op_match)], key=lambda x: expr_priority(x[0])):
        arg1, arg2 = parsed_args_roots[idx], parsed_args_roots[idx + 1]
        
        arg1_root, arg2_root = root_from(G, arg1), root_from(G, arg2)
        # print(op, arg1_root, arg2_root)
        if G.nodes(data='op')[arg1_root] == op and G.nodes(data='op')[arg2_root] != op:
            G.add_edge(arg1_root, arg2_root)
            new_name = arg1_root + op + arg2_root
            nx.relabel_nodes(G, {arg1_root: new_name}, copy=False)
            G.nodes[new_name]['args'].append(arg2_root)
        elif G.nodes(data='op')[arg2_root] == op and G.nodes(data='op')[arg1_root] != op:
            G.add_edge(arg2_root, arg1_root)
            new_name = arg2_root + op + arg1_root
            nx.relabel_nodes(G, {arg2_root: new_name}, copy=False)
            G.nodes[new_name]['args'].append(arg1_root)
        elif G.nodes(data='op')[arg2_root] == op and G.nodes(data='op')[arg1_root] == op:
            print("FUCK") # тут можно стянуть их в одну вершину с оператором
        else:
            op_idx = '{}{}{}'.format(arg1_root, op, arg2_root)
            G.add_nodes_from([(op_idx, {'type': OP_TYPE, 'op': op, 'args': [arg1_root, arg2_root]})])
            G.add_edges_from([(op_idx, arg1_root), (op_idx, arg2_root)])

    return G

def set_facts(G: nx.DiGraph, facts: List[str]):
    for fact in facts:
        if fact in G:
            G.nodes[fact]['value'] = True
        else:
            G.add_nodes_from([(fact, {'type': ARG_TYPE, 'value': True})])

def reset_facts(G: nx.DiGraph, facts: List[str]):
    for n in G.nodes:
        G.nodes[n]['value'] = False
    set_facts(G, facts)

def build_total_graph(rules: List[tuple], facts: List[str]):
    G = nx.DiGraph()

    for implicator, implied in rules:
        g_implicator, g_implied = build_expr_graph(implicator), build_expr_graph(implied)

        G.update(g_implicator)
        G.update(g_implied)
        G.add_edge(get_zero_indegree_node(g_implicator), get_zero_indegree_node(g_implied), edge_type=IMPLICATION_TYPE)

    set_facts(G, facts)

    return G

def evaluate_expression(G: DiGraph, node: str, askers_stack: AskerStack = None) -> int:
    if node not in G.nodes:
        return ANSWER_FALSE

    if askers_stack is None:
        askers_stack = AskerStack()
    padding = ''.join([' '] * (AskerStack.padding_unit_len * len(askers_stack)))
    print_log(f'{padding}{node}=?')
    result = eval_expr_node(G, node, askers_stack=askers_stack)
    print_log(f'{padding}{node}={to_final_answer(result)}')
    return result

def eval_expr_node(G: DiGraph, node: str, askers_stack: AskerStack) -> int:
    if node not in G.nodes:
        return ANSWER_FALSE
    latest_asker = askers_stack.latest_asker()
    
    if G.nodes[node]['type'] == ARG_TYPE:
        if G.nodes[node]['value'] is True:
            return ANSWER_TRUE
        else:
            if askers_stack.has(node):
                return ANSWER_UNDETERMINED
            # тестим (или выражаем) выражения, из которых следует это значение
            implicators_results = [evaluate_expression(G, n, askers_stack=askers_stack.grow(node)) for n in G.predecessors(node) if n != latest_asker]
            return max(implicators_results) if len(implicators_results) > 0 else ANSWER_DEFAULT
    elif G.nodes[node]['type'] == OP_TYPE:
        if latest_asker not in (expr_args := G.nodes[node]['args']):
            # если выражение уже из чего-либо следует, можно и не вычислять его
            implicator_results = [evaluate_expression(G, n, askers_stack=askers_stack.grow(node)) for n in G.predecessors(node) if not askers_stack.has(n)]
            if len(implicator_results) > 0 and max(implicator_results) == ANSWER_TRUE:
                return ANSWER_TRUE
 
            arg_values = [evaluate_expression(G, n, askers_stack=askers_stack.grow(node)) for n in expr_args]
            trues_count = sum([int(x == ANSWER_TRUE) for x in arg_values])
            if G.nodes[node]['op'] == '+':
                return ANSWER_TRUE if len(arg_values) == trues_count else ANSWER_FALSE # все == True
            elif G.nodes[node]['op'] == '|':
                return ANSWER_TRUE if trues_count > 0 else ANSWER_FALSE # хоть один == True
            elif G.nodes[node]['op'] == '^':
                return ANSWER_TRUE if trues_count == 1 else ANSWER_FALSE # ровно один == True
            elif G.nodes[node]['op'] == '!':
                return ANSWER_TRUE if trues_count == 0 else ANSWER_FALSE # отрицание. Тут всегда будет один агрумент, написано для едиообразия
        else:
            # может следовать из нескольких вещей, так что берем условие "хоть один"
            is_this_op_true = max([evaluate_expression(G, n, askers_stack=askers_stack.grow(node)) for n in G.predecessors(node)] + [evaluate_expression(G, node, askers_stack=askers_stack.grow(node))]) # да, мы тестим еще и само это выражение - ведь оно может быть истинной независимо от того, следует оно из чего-либо, или нет (например A|B, где B - факт) 
            # т.е. следует ли это выражение из чего-либо
            if is_this_op_true != ANSWER_TRUE:
                return is_this_op_true # т.е. если само выражение не True, нам уже нечего проверять, т.к. из лжи может следовать что угодно (из undetermined, предполагается, что следует undetermined, так что пишу так)

            if G.nodes[node]['op'] == '+':
                return ANSWER_TRUE
            elif G.nodes[node]['op'] == '|':
                other_args = [evaluate_expression(G, n, askers_stack=askers_stack.grow(node)) for n in expr_args if n != latest_asker]
                if np.all([x == ANSWER_FALSE for x in other_args]):
                    return ANSWER_TRUE
                else:
                    return ANSWER_UNDETERMINED
            elif G.nodes[node]['op'] == '^':
                other_args = [evaluate_expression(G, n, askers_stack=askers_stack.grow(node)) for n in expr_args if n != latest_asker]
                if np.all([x == ANSWER_FALSE for x in other_args]):
                    return ANSWER_TRUE
                elif np.any([x == ANSWER_TRUE for x in other_args]):
                    return ANSWER_FALSE
                else:
                    return ANSWER_UNDETERMINED
            elif G.nodes[node]['op'] == '!':
                return ANSWER_FALSE



def direct_implies(G: DiGraph, node: str) -> dict:
    all_successors = set(G.successors(node))
    args = G.nodes(data='args')[node]
    args = set(args) if (isinstance(args, list) and G.nodes(data='op')[node] != '+') else set([])

    result = {}
    for r in all_successors - args:
        is_negation = G.nodes(data='op')[r] == '!'
        ss = list(G.successors(r))
        key = r if not is_negation else ss[0]
        result[key] = not is_negation
    return result

def all_implies(G: DiGraph, node: str) -> set:
    to_check = direct_implies(G, node)
    result = set()

    while len(to_check) > 0:
        n = to_check.pop()
        result.add(n)
        to_check.update(direct_implies(G, n) - result)

    return result

def do_contradiction_test(G:DiGraph):
    try:
        check_for_contraditions(G)
    except:
        pass

def check_for_contraditions(G: DiGraph):
    for node, data in G.nodes(data=True):
        to_check = direct_implies(G, node)
        result = {}

        while len(to_check) > 0:
            n, t = to_check.popitem()
            # if n in result.keys() and result[n] != t:
            #     print("FEFE", n)
            result[n] = t
            if t:
                to_check.update({k: v for k, v in direct_implies(G, n).items() if k not in result.keys()})

        # print(node, result)

def print_log(*args):
    if os.environ['VERBOSE'] == '1':
        print(*args)

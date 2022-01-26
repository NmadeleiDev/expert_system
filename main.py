import sys
from source_parser import parse_file, parse_source_iteratively
import argparse
import os
from utils import *
from graph_operations import build_total_graph, evaluate_expression


parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-f', '--file', dest='source', type=str, default=None, help='File to read input from (default stdin)')
parser.add_argument('-i', '--iteractive', dest='iteractive', default=False, action='store_true',
                    help='If true, will parse inputs intercatively')
parser.add_argument('-g', '--save-graph', dest='save', default=False, action='store_true',
                    help='Save generated graph (only in non-intercative mode)')
parser.add_argument('-v', '--verbose', dest='verbose', default=False, action='store_true',
                    help='Print how answer is figured out')

args = parser.parse_args()

os.environ['VERBOSE'] = '1' if args.verbose else '0'

def main():
    if not args.iteractive:
        rules, facts, query = parse_file(args.source)
        rules = check_rules(rules)

        solving_grahp = build_total_graph(rules, facts)
        print("Answers:")
        for q in query:
            print('{} is {}'.format(q, to_final_answer(evaluate_expression(solving_grahp, q))))

        if args.save:
            save_graph_to_file(solving_grahp)
    else:
        if args.save:
            print("Warning: graph will not be saved due to intercative mode")
        if args.source is not None:
            rules, facts, query = parse_file(args.source)
            rules = check_rules(rules)
            solving_grahp = build_total_graph(rules, facts)
            print("Answers:")
            for q in query:
                print('{} is {}'.format(q, to_final_answer(evaluate_expression(solving_grahp, q))))
        else:
            rules = []

        for more_rules, facts, query in parse_source_iteratively(sys.stdin):
            rules.extend(more_rules)
            solving_grahp = build_total_graph(rules, facts)
            print("Answers:")
            for q in query:
                print('{} is {}'.format(q, to_final_answer(evaluate_expression(solving_grahp, q))))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\bBye!')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception as e:
        print('Programm failed:', str(e))
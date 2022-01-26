from ctypes import Union
from os import path
from typing import Iterable, List, Tuple

from numpy import iterable
from utils import *
import re

def parse_rule(inp: str) -> List[tuple]:
    imply_sign = inp.find('=>')
    equal_sign = inp.find('<=>')
    if (equal_sign >= 0):
        p1, p2 = inp[:equal_sign].strip(), inp[equal_sign + 3:].strip()
        result = [(p1, p2), (p2, p1)]
    elif (imply_sign >= 0):
        p1, p2 = inp[:imply_sign].strip(), inp[imply_sign + 2:].strip()
        result = [(p1, p2)]
    else:
        return []
    
    if len(p1) == 0 or len(p2) == 0:
        print(f"Warn: some of the expressions in rule '{inp}' are empty. Will skip it.")
    if p1 == p2:
        print(f"Warn: Rule is a tautology: '{inp}'")
        return []
    return result

def parse_facts(inp: str) -> list:
    if inp[0] == '=':
        wrong_input = re.search("^(?![A-Z])", inp[1:])
        if wrong_input is not None and len(wrong_input.groups()) > 0:
            print(f"Facts string is incorrect: {inp}", re.search("^(?![A-Z])", inp[1:]).groups())
            return []
            # exit(1)
        return list(inp[1:])
    else:
        return []

def parse_query(inp: str) -> list:
    if inp[0] == '?':
        if re.search("^(?![A-Z])", inp[1:]) is not None:
            print(f"Query string is incorrect: {inp}")
            return []
        return list(inp[1:])
    else:
        return []

def parse_answer(inp: str):
    if inp.endswith(':False') or inp.endswith(':True'):
        return inp[2:3], inp.endswith(':True')
    else:
        return None

def clean_line(line: str) -> str:
    return line.split('#')[0].strip().replace('\t', ' ').replace(' ', '')

def parse_file(p: str) -> Tuple[list, list, list]:
    if path.isfile(p) :
        with open(p, 'r') as f:
            return parse_all_source(f.read())
    else:
        raise Exception(f"File {p} not found")

def parse_all_source(raw: str) -> Tuple[List[tuple], set, list]:
    rules = []
    facts = set()
    query = []
    
    for line in map(str.strip, raw.split('\n')):
        line = clean_line(line)
        if line == "":
            continue

        rules.extend(parse_rule(line))
        facts.update(parse_facts(line))
        query.extend(parse_query(line))

    return rules, facts, query

def parse_source_iteratively(raw: iterable, read_answers=False) -> Iterable[tuple]:
    rules = []
    facts = set()
    query = []
    answers = {}
    
    for line in map(str.strip, raw):
        clear_line = clean_line(line)

        if len(clear_line) > 0:
            rules.extend(parse_rule(clear_line))
            facts.update(parse_facts(clear_line))
            q = parse_query(clear_line)
            query.extend(q)
        if (answ := parse_answer(line)) is not None:
            answers[answ[0]] = answ[1]

        yield_now = False
        if not read_answers:
            yield_now = len(q) > 0
        else:
            yield_now = len(answers) > 0 and answ is None
            
        if yield_now:
            if read_answers:
                yield (rules, facts, query, answers)
            else:
                yield (rules, facts, query)
            facts.clear()
            query.clear()
            answers.clear()

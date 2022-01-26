value_expressions = {
    '+': lambda a,b: a and b,
    '|': lambda a,b: a or b,
    '^': lambda a,b: (a or b) and not (a and b),
    '!': lambda a: not a
}

order_expr_priority = ['!', '+', '|', '^']
expr_priority = lambda x: order_expr_priority.index(x)


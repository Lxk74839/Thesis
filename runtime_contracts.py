"""Select the accepted prompt/output contract; execution scope is checked separately."""


def bound_contract(binding):
    from development_pilot import authorized
    from formal_runtime import authorized as formal
    return authorized(binding) or formal(binding)

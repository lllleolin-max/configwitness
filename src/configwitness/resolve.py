"""Shallow whole-field override; later parent wins, child wins last."""
from copy import deepcopy


def resolve(problem):
    cache = {}
    def layer(n):
        if n in cache:
            return cache[n]
        state, history = {}, {}
        for p in problem.layers[n]["parents"]:
            ps, ph = layer(p)
            for f, events in ph.items():
                history.setdefault(f, []).extend(deepcopy(events))
            state.update(ps)
        for f, v in problem.layers[n]["overrides"].items():
            state[f] = v
            history.setdefault(f, []).append({"layer": n, "value": deepcopy(v)})
        cache[n] = (state, history)
        return state, history
    for n in problem.layers:
        layer(n)
    layers = {}
    for n, (state, history) in cache.items():
        layers[n] = {"values": {f: deepcopy(v) for f, v in state.items() if type(v) is not dict},
                     "trace": deepcopy(history)}
    envs = {e: deepcopy(layers[n]) for e, n in problem.envs.items()}
    return layers, envs


def schema_errors(problem, envs):
    return [{"env": e, "field": f, "reason": "required field missing or unset"}
            for e, resolved in envs.items() for f, s in problem.fields.items()
            if s.get("required", True) and f not in resolved["values"]]

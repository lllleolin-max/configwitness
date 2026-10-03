"""Shallow whole-field override; later parent wins, child wins last."""
from copy import deepcopy
from .model import InputError


def resolve(problem, include_trace=False, max_trace_events=20_000):
    cache = {}
    event_count = 0
    for n in problem.order:
        state, history = {}, {}
        for p in problem.layers[n]["parents"]:
            ps, ph = cache[p]
            if include_trace:
                for f, events in ph.items():
                    event_count += len(events)
                    if event_count > max_trace_events:
                        raise InputError(f"exact trace exceeds {max_trace_events} cached provider events; validate/search do not expand provenance")
                    history.setdefault(f, []).extend(deepcopy(events))
            state.update(ps)
        for f, v in problem.layers[n]["overrides"].items():
            state[f] = v
            if include_trace:
                event_count += 1
                if event_count > max_trace_events:
                    raise InputError(f"exact trace exceeds {max_trace_events} cached provider events")
                history.setdefault(f, []).append({"layer": n, "value": deepcopy(v)})
        cache[n] = (state, history)
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

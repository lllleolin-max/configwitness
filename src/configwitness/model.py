"""Strict custom JSON format, not CUE/Rego. Validate before resolving."""
from __future__ import annotations

import copy
import json
from pathlib import Path


class InputError(ValueError):
    """Unsupported, ambiguous or malformed input."""


def fail(message):
    raise InputError(message)


def obj(value, where, required, optional=()):
    if type(value) is not dict:
        fail(f"{where}: expected object")
    if set(value) - set(required) - set(optional) or set(required) - set(value):
        fail(f"{where}: keys must be {list(required)} plus optional {list(optional)}")


def integer(value, where, minimum=None):
    if type(value) is not int or (minimum is not None and value < minimum):
        fail(f"{where}: expected integer" + (f" >= {minimum}" if minimum is not None else ""))


def name(value, where):
    if type(value) is not str or not value or len(value) > 128 or any(ord(c) < 32 for c in value):
        fail(f"{where}: expected nonempty identifier <=128 characters without controls")


def seq(value, where, nonempty=False):
    if type(value) is not list or (nonempty and not value):
        fail(f"{where}: expected {'nonempty ' if nonempty else ''}list")


def token(value):
    """Type-tagged scalar identity: Python's True == 1 is unsuitable here."""
    return (type(value).__name__, value)


def scalar(value, spec, where):
    if value is None and spec.get("nullable", False):
        return
    wanted = {"int": int, "string": str, "bool": bool}[spec["type"]]
    if type(value) is not wanted:
        fail(f"{where}: expected {spec['type']}" + (" or null" if spec.get("nullable") else ""))


def override(value, spec, where):
    if type(value) is dict:
        if value != {"$unset": True} or type(value.get("$unset")) is not bool:
            fail(f"{where}: only {{$unset: true}} is a valid override marker")
    else:
        scalar(value, spec, where)


class Problem:
    """Validated snapshot; callers should create a new instance after editing."""

    def __init__(self, data):
        try:
            self.data = copy.deepcopy(data)
        except RecursionError as exc:
            raise InputError("input nesting exceeds runtime copy limit") from exc
        d = self.data
        obj(d, "document", ("version", "fields", "layers", "environments", "constraints", "edits", "protected"), ("edit_scope", "description"))
        if type(d["version"]) is not int or d["version"] != 1:
            fail("document.version: only 1 supported")
        if "description" in d and type(d["description"]) is not str:
            fail("description: expected string")
        self.fields = d["fields"]
        if type(self.fields) is not dict or not self.fields:
            fail("fields: expected nonempty object")
        for f, s in self.fields.items():
            name(f, "field name")
            obj(s, f"fields.{f}", ("type",), ("nullable", "required"))
            if s["type"] not in ("int", "string", "bool"):
                fail(f"fields.{f}: unsupported type")
            for flag in ("nullable", "required"):
                if flag in s and type(s[flag]) is not bool:
                    fail(f"fields.{f}.{flag}: expected bool")
        seq(d["layers"], "layers", True)
        self.layers = {}
        for l in d["layers"]:
            obj(l, "layer", ("id", "parents", "overrides"))
            name(l["id"], "layer.id")
            if l["id"] in self.layers:
                fail(f"duplicate layer id: {l['id']}")
            self.layers[l["id"]] = l
            seq(l["parents"], "parents")
            for p in l["parents"]:
                name(p, "parent")
            if len(set(l["parents"])) != len(l["parents"]):
                fail("duplicate parent")
            if type(l["overrides"]) is not dict:
                fail("overrides: expected object")
            for f, v in l["overrides"].items():
                self.field(f)
                override(v, self.fields[f], f"layer {l['id']}.{f}")
        for l in self.layers.values():
            if any(p not in self.layers for p in l["parents"]):
                fail(f"missing parent of {l['id']}")
        # Iterative DFS preserves parent precedence but avoids input-order-dependent
        # recursion failure on a perfectly legal deep acyclic graph.
        seen, active, self.order = set(), set(), []
        for root in self.layers:
            if root in seen:
                continue
            stack = [(root, False)]
            while stack:
                layer, exiting = stack.pop()
                if exiting:
                    active.remove(layer)
                    seen.add(layer)
                    self.order.append(layer)
                    continue
                if layer in active:
                    fail(f"inheritance cycle at {layer}")
                if layer in seen:
                    continue
                active.add(layer)
                stack.append((layer, True))
                stack.extend((p, False) for p in reversed(self.layers[layer]["parents"]))
        seq(d["environments"], "environments", True)
        self.envs = {}
        for e in d["environments"]:
            obj(e, "environment", ("id", "layer"))
            name(e["id"], "environment.id")
            name(e["layer"], "environment.layer")
            if e["id"] in self.envs or e["layer"] not in self.layers:
                fail("duplicate environment or unknown layer")
            self.envs[e["id"]] = e["layer"]
        seq(d["constraints"], "constraints")
        ids = set()
        for c in d["constraints"]:
            if type(c) is not dict:
                fail("constraint: expected object")
            kind = c.get("kind")
            common = ("id", "kind", "envs", "field")
            if kind in ("range", "sum"):
                obj(c, "constraint", common, ("min", "max"))
                if not ("min" in c or "max" in c):
                    fail("range/sum requires min or max")
                for bound in ("min", "max"):
                    if bound in c:
                        integer(c[bound], f"constraint.{bound}")
                if c.get("min", 0) > c.get("max", c.get("min", 0)) and "min" in c and "max" in c:
                    fail("constraint min exceeds max")
                self.field(c["field"], "int")
            elif kind in ("equal", "distinct"):
                obj(c, "constraint", common)
                self.field(c["field"])
            elif kind == "allowed":
                obj(c, "constraint", common + ("values",))
                self.field(c["field"])
                seq(c["values"], "allowed.values", True)
                for v in c["values"]:
                    scalar(v, self.fields[c["field"]], "allowed value")
                if len({token(v) for v in c["values"]}) != len(c["values"]):
                    fail("duplicate allowed value")
            elif kind == "failover":
                obj(c, "constraint", ("id", "kind", "primary", "backup", "replicas", "region", "min_backup"))
                self.field(c["replicas"], "int")
                self.field(c["region"], "string")
                integer(c["min_backup"], "min_backup", 1)
                name(c["primary"], "failover.primary")
                name(c["backup"], "failover.backup")
                if c["primary"] not in self.envs or c["backup"] not in self.envs or c["primary"] == c["backup"]:
                    fail("failover requires distinct known primary and backup")
            else:
                fail(f"unsupported constraint kind: {kind}")
            name(c["id"], "constraint.id")
            if c["id"] in ids:
                fail("duplicate constraint id")
            ids.add(c["id"])
            if "envs" in c:
                seq(c["envs"], "constraint.envs", True)
                for e in c["envs"]:
                    name(e, "constraint.env")
                if len(set(c["envs"])) != len(c["envs"]) or any(e not in self.envs for e in c["envs"]):
                    fail("constraint envs must be unique known identifiers")
        seq(d["edits"], "edits")
        scope = d.get("edit_scope", "leaf")
        if scope not in ("leaf", "declared-layers"):
            fail("edit_scope: expected leaf or declared-layers")
        parents = {p for l in self.layers.values() for p in l["parents"]}
        targets = set()
        for e in d["edits"]:
            obj(e, "edit", ("layer", "field", "options"))
            self.field(e["field"])
            name(e["layer"], "edit.layer")
            if e["layer"] not in self.layers:
                fail("unknown edit layer")
            if scope == "leaf" and (e["layer"] in parents or e["layer"] not in self.envs.values()):
                fail("leaf edits require environment layers with no children")
            target = (e["layer"], e["field"])
            if target in targets:
                fail("duplicate edit target")
            targets.add(target)
            seq(e["options"], "edit.options", True)
            options = set()
            for o in e["options"]:
                obj(o, "option", ("op", "cost"), ("value",))
                integer(o["cost"], "option.cost", 0)
                if o["op"] == "set":
                    if "value" not in o:
                        fail("set requires value")
                    scalar(o["value"], self.fields[e["field"]], "option value")
                elif o["op"] in ("unset", "remove"):
                    if "value" in o:
                        fail("unset/remove forbids value")
                else:
                    fail("option.op must be set, unset or remove")
                identity = (o["op"], token(o.get("value")))
                if identity in options:
                    fail("duplicate edit option")
                options.add(identity)
        seq(d["protected"], "protected")
        protected = set()
        for p in d["protected"]:
            if type(p) is not dict or set(p) not in ({"env", "field"}, {"layer", "field"}):
                fail("protected: expected env/field or layer/field")
            self.field(p["field"])
            k = "env" if "env" in p else "layer"
            name(p[k], "protected target")
            if p[k] not in (self.envs if k == "env" else self.layers):
                fail("unknown protected target")
            identity = (k, p[k], p["field"])
            if identity in protected:
                fail("duplicate protected target")
            protected.add(identity)

    def field(self, f, wanted=None):
        name(f, "field reference")
        if f not in self.fields or (wanted is not None and self.fields[f]["type"] != wanted):
            fail(f"unknown field or wrong constraint type: {f}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    """Strict duplicate-key/nonfinite handling, shared by input and proposals."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"),
                          parse_constant=lambda x: fail(f"nonfinite number: {x}"),
                          object_pairs_hook=unique_object)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise InputError(str(exc)) from exc


def load(path):
    """Read UTF-8 JSON. Parsing/schema errors are InputError."""
    return Problem(read_json(path))

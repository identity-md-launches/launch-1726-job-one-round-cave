#!/usr/bin/env python3
"""Validate and summarize saved call evidence. Offline; standard library only."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
CORE_PATH = HERE.parent / "call-rehearsal" / "rehearse.py"
if not CORE_PATH.is_relative_to(Path.cwd().resolve()):
    raise ValueError("run from a workspace containing the tool and its dependency")
SPEC = importlib.util.spec_from_file_location("report_rehearse_core", CORE_PATH)
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)
FIELDS = {"schema", "source", "chain_id", "block", "call", "returns",
          "code_present", "outcome"}


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        core.require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("non-finite JSON number: " + value)


def summarize(value):
    """Recompute interpretation from raw evidence; ignore no unknown fields."""
    core.require(isinstance(value, dict) and
                 FIELDS <= set(value) <= FIELDS | {"transport"},
                 "observation must have exactly the rehearsal fields and optional transport")
    core.require(value["schema"] == core.SCHEMA, "unsupported rehearsal schema")
    core.require(type(value["chain_id"]) is int and value["chain_id"] == 1,
                 "expected Ethereum mainnet")
    core.require(value["source"] in core.ENDPOINTS, "unknown public source")
    block = value["block"]
    core.require(isinstance(block, dict) and
                 set(block) == {"number", "hash", "timestamp"}, "invalid block fields")
    block = core.header(block)
    call = core.transaction(value["call"])
    core.require(type(value["code_present"]) is bool, "code_present must be boolean")
    outcome = value["outcome"]
    core.require(isinstance(outcome, dict) and len(outcome) == 1,
                 "outcome must contain exactly result or error")
    if "error" in outcome:
        error = core.RPCError(outcome["error"]).error
        core.require(set(error) <= {"code", "message", "data"}, "unknown RPC error fields")
        if "data" in error:
            core.data(error["data"])
    interpreted = core.interpret(outcome, value["returns"])
    if "transport" in value:
        transport = value["transport"]
        core.require(isinstance(transport, dict) and transport == {
            "kind": "contributor-relay", "source_is_attribution_only": True,
            "independent_provider_verified": False} and
            type(transport["source_is_attribution_only"]) is bool and
            type(transport["independent_provider_verified"]) is bool,
            "invalid transport provenance")
    ready = value["code_present"] and interpreted["status"] in {"returned", "returned_true"}
    reason = ("validated return encoding and recorded code presence; review still required"
              if ready else "code unconfirmed, false boolean, revert, RPC failure, or unexpected ABI return")
    result = {
        "status": "ready-to-review" if ready else "withheld", "reason": reason,
        "chain_id": 1, "block": block["number"], "block_hash": block["hash"],
        "block_timestamp": block["timestamp"], "target": call["to"],
        "calldata": call["data"], "native_value": call["value"],
        "outcome": "return" if "result" in outcome else
                   "revert" if interpreted["status"] == "reverted" else "rpc-error",
        "return_bytes": interpreted.get("raw"), "returns": value["returns"],
        "interpretation": interpreted, "source": value["source"],
        "limits": "Historical provider-reported evidence only. No authenticated ABI, chain, code proof, "
                  "freshness, authority, gas, state effects or future-execution guarantee. "
                  "No transaction is signed or sent. An omitted sender remains omitted; raw returns "
                  "have no inferred meaning. ready-to-review is not approval to transact."
    }
    if "from" in call:
        result["sender"] = call["from"]
    if "transport" in value:
        result["transport"] = value["transport"].copy()
        result["limits"] += " Public source is attribution only; upstream identity is unverified."
    return result


def report(path):
    with core.workspace_path(path).open("rb") as handle:
        raw = handle.read(core.LIMIT + 1)
    core.require(len(raw) <= core.LIMIT, "observation exceeds 90 KB")
    value = json.loads(raw, object_pairs_hook=no_duplicates, parse_constant=reject_constant)
    return summarize(value)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observation", nargs="?", default=str(
        HERE.parent / "return-lens" / "zto-live-observation.json"))
    args = parser.parse_args(argv)
    try:
        result = report(args.observation)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0 if result["status"] == "ready-to-review" else 1
    except (OSError, ValueError, KeyError, TypeError, RecursionError, core.RPCError) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

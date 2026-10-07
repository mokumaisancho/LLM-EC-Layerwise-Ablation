from __future__ import annotations
import json
from typing import Any

PROTOCOL="S1C_V3_JSON_GBNF_V1"

def gbnf_literal(raw:str)->str:
    return json.dumps(raw)

def json_string_terminal(value:str)->str:
    # GBNF quoted terminal whose matched bytes are a complete JSON string,
    # e.g. value S01 -> grammar token "\"S01\"".
    return gbnf_literal(json.dumps(value))

def alts_json_strings(values:list[str])->str:
    return " | ".join(json_string_terminal(x) for x in sorted(set(values)))

def list_rule(item_rule:str,max_n:int,allow_empty:bool=True)->str:
    rows=[gbnf_literal("[]")] if allow_empty else []
    for n in range(1,max_n+1):
        body=(' ws '+gbnf_literal(",")+' ws ').join([item_rule]*n)
        rows.append(gbnf_literal("[")+" ws "+body+" ws "+gbnf_literal("]"))
    return " | ".join(rows)

def grammar_for(task:dict[str,Any])->str:
    v=task["visible"]
    train=[str(x["example_id"]) for x in v["training_examples"]]
    held=[str(x["example_id"]) for x in v["heldout_examples"]]
    types=[str(x) for x in v["type_inventory"]]
    entities=sorted({str(eid) for ex in v["heldout_examples"] for eid in ex["entity_registry"]})
    slotids=[f"S{i:02d}" for i in range(1,5)]
    J=json_string_terminal; T=gbnf_literal
    lines=[
      "root ::= ws "+T("{")+" ws "+J("discovered_slots")+" ws "+T(":")+" ws slotlist ws "+T(",")+" ws "+J("heldout_assignments")+" ws "+T(":")+" ws assignlist ws "+T(",")+" ws "+J("abstentions")+" ws "+T(":")+" ws abstainlist ws "+T("}")+" ws",
      "slotlist ::= "+list_rule("slot",4,False),
      "slot ::= "+T("{")+" ws "+J("slot_id")+" ws "+T(":")+" ws slotid ws "+T(",")+" ws "+J("arg_types")+" ws "+T(":")+" ws typelist ws "+T(",")+" ws "+J("training_members")+" ws "+T(":")+" ws memberlist ws "+T("}"),
      "typelist ::= "+list_rule("typeitem",2,True),
      "memberlist ::= "+list_rule("memberitem",4,False),
      "assignlist ::= "+list_rule("assignment",3,True),
      "assignment ::= "+T("{")+" ws "+J("example_id")+" ws "+T(":")+" ws helditem ws "+T(",")+" ws "+J("slot_id")+" ws "+T(":")+" ws slotid ws "+T(",")+" ws "+J("arguments")+" ws "+T(":")+" ws arglist ws "+T(",")+" ws "+J("polarity")+" ws "+T(":")+" ws polarity ws "+T(",")+" ws "+J("modality")+" ws "+T(":")+" ws modality ws "+T("}"),
      "arglist ::= "+list_rule("entityitem",2,True),
      "abstainlist ::= "+list_rule("abstention",3,True),
      "abstention ::= "+T("{")+" ws "+J("example_id")+" ws "+T(":")+" ws helditem ws "+T(",")+" ws "+J("status")+" ws "+T(":")+" ws "+J("AMBIGUOUS")+" ws "+T("}"),
      "slotid ::= "+alts_json_strings(slotids),
      "typeitem ::= "+alts_json_strings(types),
      "memberitem ::= "+alts_json_strings(train),
      "helditem ::= "+alts_json_strings(held),
      "entityitem ::= "+alts_json_strings(entities),
      "polarity ::= "+alts_json_strings(["POS","NEG"]),
      "modality ::= "+alts_json_strings(["ASSERTED","REQUIRED","POSSIBLE"]),
      "ws ::= [ \\t\\n\\r]*",
    ]
    return "\n".join(lines)

def canonical_valid_output(task:dict[str,Any])->dict[str,Any]:
    v=task["visible"]; train=[x["example_id"] for x in v["training_examples"]]; held=[x["example_id"] for x in v["heldout_examples"]]
    types=[v["training_examples"][0]["entity_registry"][eid]["type"] for eid in sorted(v["training_examples"][0]["entity_registry"])]
    args=sorted(v["heldout_examples"][0]["entity_registry"])
    return {
      "discovered_slots":[
        {"slot_id":"S01","arg_types":types,"training_members":train[:2]},
        {"slot_id":"S02","arg_types":types,"training_members":train[2:]},
      ],
      "heldout_assignments":[
        {"example_id":held[0],"slot_id":"S01","arguments":args,"polarity":"POS","modality":"ASSERTED"},
        {"example_id":held[1],"slot_id":"S02","arguments":args,"polarity":"POS","modality":"ASSERTED"},
      ],
      "abstentions":[{"example_id":held[2],"status":"AMBIGUOUS"}],
    }

def static_contract_check(task:dict[str,Any],grammar:str)->dict[str,Any]:
    lines={line.split("::=",1)[0].strip():line.split("::=",1)[1].strip() for line in grammar.splitlines() if "::=" in line}
    dynamic={
      "slotid":[f"S{i:02d}" for i in range(1,5)],
      "typeitem":[str(x) for x in task["visible"]["type_inventory"]],
      "memberitem":[str(x["example_id"]) for x in task["visible"]["training_examples"]],
      "helditem":[str(x["example_id"]) for x in task["visible"]["heldout_examples"]],
      "entityitem":sorted({str(eid) for ex in task["visible"]["heldout_examples"] for eid in ex["entity_registry"]}),
      "polarity":["POS","NEG"],
      "modality":["ASSERTED","REQUIRED","POSSIBLE"],
    }
    failures=[]
    for rule,vals in dynamic.items():
        expected=alts_json_strings(vals)
        if lines.get(rule)!=expected:
            failures.append({"gate":"JSON_STRING_TERMINAL_MISMATCH","rule":rule,"actual":lines.get(rule),"expected":expected})
        # Explicitly reject V2 form: direct gbnf_literal(value), which matches bare bytes.
        bad=" | ".join(gbnf_literal(x) for x in sorted(set(vals)))
        if lines.get(rule)==bad:
            failures.append({"gate":"V2_BARE_STRING_GRAMMAR_REAPPEARED","rule":rule})
    obj=canonical_valid_output(task)
    encoded=json.dumps(obj,separators=(",",":"))
    # Every key/value string in canonical object must have a corresponding quoted-byte terminal.
    required=set(["discovered_slots","heldout_assignments","abstentions","slot_id","arg_types","training_members","example_id","arguments","polarity","modality","status","AMBIGUOUS"])
    required |= {x["slot_id"] for x in obj["discovered_slots"]}
    required |= set(x["example_id"] for x in obj["heldout_assignments"]) | set(x["example_id"] for x in obj["abstentions"])
    required |= set(sum((x["training_members"] for x in obj["discovered_slots"]),[]))
    required |= set(sum((x["arg_types"] for x in obj["discovered_slots"]),[]))
    required |= set(sum((x["arguments"] for x in obj["heldout_assignments"]),[]))
    required |= set(x["polarity"] for x in obj["heldout_assignments"]) | set(x["modality"] for x in obj["heldout_assignments"])
    missing=[x for x in sorted(required) if json_string_terminal(x) not in grammar]
    if missing: failures.append({"gate":"CANONICAL_OUTPUT_STRING_TERMINAL_MISSING","values":missing})
    return {"pass":not failures,"failure_count":len(failures),"failures":failures,"canonical_json":encoded}
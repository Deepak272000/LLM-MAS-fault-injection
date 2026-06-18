"""
Minimal diagnostic: confirm fi module identity and FAULT_MODE on SPEED.
Run from emailserviceagent/ directory.
"""
import os, sys
from unittest.mock import MagicMock

# Stubs (same as test_fault_injection.py)
_mock_lg = MagicMock()
_mock_lg.END = "__end__"
_mock_lg.StateGraph = MagicMock()
sys.modules.setdefault("langgraph", MagicMock())
sys.modules["langgraph.graph"] = _mock_lg
sys.modules.setdefault("grpc", MagicMock())
sys.modules.setdefault("demo_pb2", MagicMock())
sys.modules.setdefault("demo_pb2_grpc", MagicMock())

print(f"Python: {sys.version}")
print(f"CWD:    {os.getcwd()}")
print(f"sys.path[0]: {sys.path[0]}")
print()

for fault_mode in ("NONE", "FM_3_1"):
    os.environ["FAULT_MODE"] = fault_mode
    sys.modules.pop("app.fault_injection", None)

    import app.fault_injection as fi_mod
    import app.graph as graph_mod
    graph_mod.fi = fi_mod

    node_fi = graph_mod.run_agent_node.__globals__.get("fi")

    print(f"=== {fault_mode} ===")
    print(f"  fi_mod.FAULT_MODE           = {fi_mod.FAULT_MODE!r}")
    print(f"  fi_mod is graph_mod.fi      = {fi_mod is graph_mod.fi}")
    print(f"  fi_mod is node_fi           = {fi_mod is node_fi}")
    print(f"  id(fi_mod)                  = {id(fi_mod)}")
    print(f"  id(graph_mod.fi)            = {id(graph_mod.fi)}")
    print(f"  id(node_fi)                 = {id(node_fi)}")
    print(f"  fi_mod file                 = {getattr(fi_mod, '__file__', 'N/A')}")
    print(f"  graph_mod.fi file           = {getattr(graph_mod.fi, '__file__', 'N/A')}")
    if node_fi:
        print(f"  node_fi.FAULT_MODE          = {node_fi.FAULT_MODE!r}")
        print(f"  node_fi file                = {getattr(node_fi, '__file__', 'N/A')}")
    else:
        print(f"  node_fi                     = None (fi NOT in graph globals!)")

    # Simulate what the node does: clear then record
    fi_mod.clear_lkw()
    fi_mod.record_checkpoint("TEST_STEP", {"mode": fault_mode})
    lkw = fi_mod.get_lkw()
    print(f"  After record_checkpoint: len(fi_mod.get_lkw()) = {len(lkw)}")
    if lkw:
        print(f"    entry[0].fault_mode = {lkw[0].get('fault_mode')!r}")
    print()

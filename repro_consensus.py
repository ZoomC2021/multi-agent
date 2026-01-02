
from consensus_system.manager import ConsensusManager
from consensus_system.agent import ConsensusAgent

# Mock agents with different return types
class MockAgent(ConsensusAgent):
    def __init__(self, id, val):
        super().__init__(id, "role", "instr", val)

print("Verifying ConsensusManager type handling...")

# Case 1: Complex Objects (e.g. dicts)
# Logic: If majority strategy converts to string, it might return a string representation instead of the object
agent1 = MockAgent("a1", {"a": 1})
agent2 = MockAgent("a2", {"a": 1})
agent3 = MockAgent("a3", {"b": 2})

manager = ConsensusManager(agents=[agent1, agent2, agent3])
res = manager.run_consensus(strategy="majority")

print(f"Consensus Result: {res['consensus_value']}")
print(f"Type: {type(res['consensus_value'])}")

if isinstance(res['consensus_value'], str) and res['consensus_value'] == "{'a': 1}":
    print("ISSUE DETECTED: Consensus value is a string, expected dict.")
elif isinstance(res['consensus_value'], dict):
    print("SUCCESS: Consensus value is a dict.")
else:
    print(f"UNKNOWN RESULT: {res['consensus_value']}")

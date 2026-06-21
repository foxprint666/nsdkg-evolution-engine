# ==========================================
# Copyright (c) 2026
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==========================================

import os
import re
import math
import json
import random
import difflib
import threading
import networkx as nx
from openai import OpenAI

# Predefined scenarios for mock generation to ensure the engine works out-of-the-box
MOCK_SCENARIOS = [
    {
        "red_action": "Inject_DivZero",
        "red_description": "Injected zero division in auth.py user registration counter limit calculation.",
        "target_file": "auth.py",
        "mutated_code": "def register_user(username, password):\n    # Red injected division by zero\n    limit = 0\n    rate = 10 / limit\n    return True",
        "error_type": "ZeroDivisionError",
        "stderr": "Traceback (most recent call last):\n  File \"sandbox_target.py\", line 4, in register_user\n    rate = 10 / limit\nZeroDivisionError: division by zero",
        "blue_strategy": "SafeLimitCheck",
        "blue_description": "Added check to prevent division by zero in registration counter.",
        "patched_code": "def register_user(username, password):\n    limit = 0\n    rate = 10 / limit if limit != 0 else 0\n    return True",
        "token_cost_red": 150,
        "token_cost_blue": 200,
    },
    {
        "red_action": "Corrupt_SQL_Syntax",
        "red_description": "Corrupted SQL query syntax in db.py for retrieval logic.",
        "target_file": "db.py",
        "mutated_code": "def query_user(user_id):\n    # Red corrupted SQL syntax\n    query = \"SELECT FROM users WHERE id = \" + user_id\n    raise SyntaxError(\"unbalanced sql query parenthesis\")",
        "error_type": "SyntaxError",
        "stderr": "Traceback (most recent call last):\n  File \"sandbox_target.py\", line 3, in query_user\nSyntaxError: unbalanced sql query parenthesis",
        "blue_strategy": "ParametrizeSQL",
        "blue_description": "Sanitized SQL query and fixed retrieval parameters.",
        "patched_code": "def query_user(user_id):\n    query = f\"SELECT * FROM users WHERE id = {user_id}\"\n    return {'id': user_id, 'role': 'user'}",
        "token_cost_red": 180,
        "token_cost_blue": 220,
    },
    {
        "red_action": "Param_Type_Mismatch",
        "red_description": "Changed payment amount processing parameter to string instead of float.",
        "target_file": "app_logic.py",
        "mutated_code": "def process_payment(amount):\n    # Red injected parameter type mismatch\n    tax = \"0.08\"\n    return amount + tax",
        "error_type": "TypeError",
        "stderr": "Traceback (most recent call last):\n  File \"sandbox_target.py\", line 4, in process_payment\nTypeError: can only concatenate str (not \"float\") to str",
        "blue_strategy": "CastParameters",
        "blue_description": "Cast tax rate and amount to matching numeric types.",
        "patched_code": "def process_payment(amount):\n    tax = 0.08\n    return float(amount) + tax",
        "token_cost_red": 140,
        "token_cost_blue": 190,
    },
    {
        "red_action": "Corrupt_Config_Key",
        "red_description": "Accessed non-existent encryption secret key in configuration.",
        "target_file": "db.py",
        "mutated_code": "def get_config():\n    cfg = {'db_port': 3306}\n    # Red accessed invalid key\n    key = cfg['secret_key']\n    return key",
        "error_type": "KeyError",
        "stderr": "Traceback (most recent call last):\n  File \"sandbox_target.py\", line 4, in get_config\nKeyError: 'secret_key'",
        "blue_strategy": "SafeDictGet",
        "blue_description": "Implemented dict.get fallback defaults to prevent KeyError.",
        "patched_code": "def get_config():\n    cfg = {'db_port': 3306}\n    key = cfg.get('secret_key', 'fallback_secret')\n    return key",
        "token_cost_red": 160,
        "token_cost_blue": 210,
    },
    {
        "red_action": "Infinite_Loop_Timeout",
        "red_description": "Injected endless loop while waiting for external response.",
        "target_file": "auth.py",
        "mutated_code": "def verify_session(session_id):\n    # Red injected infinite loop\n    while True:\n        pass\n    return True",
        "error_type": "TimeoutError",
        "stderr": "TimeoutError: Execution exceeded 3.0s limit",
        "blue_strategy": "LimitLoopIterations",
        "blue_description": "Added timeout check and iteration limit in session verification.",
        "patched_code": "def verify_session(session_id):\n    max_retries = 10\n    while max_retries > 0:\n        max_retries -= 1\n    return True",
        "token_cost_red": 200,
        "token_cost_blue": 250,
    }
]

class SimulatedCodebase:
    def __init__(self):
        self.files = {
            "auth.py": "def register_user(username, password):\n    limit = 10\n    rate = 10 / limit\n    return True\n\ndef verify_session(session_id):\n    return True",
            "db.py": "def query_user(user_id):\n    return {'id': user_id, 'role': 'user'}\n\ndef get_config():\n    cfg = {'db_port': 3306, 'secret_key': 'abc'}\n    return cfg.get('secret_key')",
            "app_logic.py": "def process_payment(amount):\n    tax = 0.08\n    return float(amount) + tax"
        }

    def get_lines_of_code(self) -> int:
        return sum(len(content.splitlines()) for content in self.files.values())

class ColosseumSandboxEnv:
    def __init__(self):
        self.codebase = SimulatedCodebase()
        self.uptime_ticks = 0
        self.total_ticks = 0
        self.token_budget_red = 100000
        self.token_budget_blue = 100000
        self.graph = nx.DiGraph()
        self.lock = threading.Lock()
        self.scenario_index = 0
        self.history_logs = []

    def get_uptime_percentage(self) -> float:
        if self.total_ticks == 0:
            return 100.0
        return (self.uptime_ticks / self.total_ticks) * 100.0

    def calculate_loc_diff(self, original_code: str, new_code: str) -> int:
        """Calculates total lines changed (inserted + deleted)."""
        diff = difflib.ndiff(original_code.splitlines(), new_code.splitlines())
        changes = 0
        for line in diff:
            if line.startswith('+ ') or line.startswith('- '):
                changes += 1
        return changes

    def execute_codebase(self, test_mutation_file=None, mutated_code=None) -> dict:
        """Simulates codebase evaluation, returning success/failure and logs."""
        # Temporary load mutations if specified
        temp_files = dict(self.codebase.files)
        if test_mutation_file and mutated_code is not None:
            temp_files[test_mutation_file] = mutated_code

        # Run checks. If code has error tokens or matches MOCK scenarios, return mock traceback
        for scenario in MOCK_SCENARIOS:
            tgt = scenario["target_file"]
            if temp_files.get(tgt) == scenario["mutated_code"]:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": scenario["stderr"],
                    "error_type": scenario["error_type"]
                }
        
        # Check standard checks to verify if division by zero remains or if there's any timeout/errors
        # (This handles both mock evaluation and dynamic patching checks)
        for name, code in temp_files.items():
            if "10 / limit" in code and "limit = 0" in code and "if limit != 0" not in code:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "ZeroDivisionError: division by zero in " + name,
                    "error_type": "ZeroDivisionError"
                }
            if "while True" in code and "pass" in code:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "TimeoutError: Execution exceeded 3.0s limit",
                    "error_type": "TimeoutError"
                }
            if "query = \"SELECT FROM users\"" in code or "raise SyntaxError" in code:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "SyntaxError: unbalanced sql query parenthesis",
                    "error_type": "SyntaxError"
                }
            if "amount + tax" in code and "tax = \"0.08\"" in code:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "TypeError: can only concatenate str (not \"float\") to str",
                    "error_type": "TypeError"
                }
            if "cfg['secret_key']" in code and "'db_port'" in code and "'secret_key'" not in code:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "KeyError: 'secret_key' in " + name,
                    "error_type": "KeyError"
                }

        return {
            "success": True,
            "stdout": "All compilation tests and unit checks passed successfully.",
            "stderr": "",
            "error_type": None
        }

def get_qwen_mutation(client: OpenAI, codebase: dict, role: str, context: str, error_trace: str = "") -> dict:
    """Invokes Qwen API (if configured) or falls back to mock responses."""
    if client and client.api_key and "dummy" not in client.api_key:
        try:
            if role == "red":
                prompt = (
                    f"You are the RED ADVERSARY agent. Here is the codebase dictionary:\n{json.dumps(codebase)}\n"
                    f"History path:\n{context}\n"
                    f"Generate a malicious code injection, syntax error, or logical exploit in one file.\n"
                    f"Return ONLY valid JSON in the format:\n"
                    f'{{"target_file": "file_name", "mutated_code": "entire code of the modified file", "red_action": "ShortName", "red_description": "Explanation", "error_type": "ExpectedErrorType", "stderr": "MockStderrTrace"}}'
                )
            else:
                prompt = (
                    f"You are the BLUE REMEDIATION agent. Here is the codebase dictionary:\n{json.dumps(codebase)}\n"
                    f"And the traceback error:\n{error_trace}\n"
                    f"History path:\n{context}\n"
                    f"Fix this bug or patch the security vulnerability.\n"
                    f"Return ONLY valid JSON in the format:\n"
                    f'{{"target_file": "file_name", "patched_code": "entire code of the patched file", "blue_strategy": "ShortName", "blue_description": "Explanation", "token_cost": 300}}'
                )
            
            response = client.chat.completions.create(
                model="qwen3.7-max",
                messages=[
                    {"role": "system", "content": "You are a cyber security agent. Return JSON ONLY."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            raw_content = response.choices[0].message.content.strip()
            if raw_content.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\n|```$", "", raw_content, flags=re.MULTILINE).strip()
            else:
                cleaned = raw_content
            data = json.loads(cleaned)
            # Add defaults
            if role == "red":
                data["token_cost_red"] = len(prompt) // 4 + 200
            else:
                data["token_cost_blue"] = len(prompt) // 4 + 250
            return data
        except Exception as e:
            # Fall back to mock quietly on exception
            pass
            
    # Mock fallback sequence generator
    return None

def colosseum_simulation_tick(env: ColosseumSandboxEnv, client: OpenAI = None, decay_rate: float = 0.25) -> dict:
    """
    Executes one simulation tick.
    - Red Adversary infects a file.
    - Sandbox evaluates.
    - If broken, Blue Remediation patches it.
    - Active ingestion indexes events to NetworkX (safely locked).
    - Synaptic decay and pruning cycle clean up routes.
    - Uptime and metrics evaluated by the Judge.
    """
    tick_logs = []
    
    # Pick next mock scenario or try Qwen
    history_ctx = get_compressed_history(env)
    qwen_red = get_qwen_mutation(client, env.codebase.files, "red", history_ctx)
    
    scenario = MOCK_SCENARIOS[env.scenario_index % len(MOCK_SCENARIOS)]
    
    if qwen_red:
        red_action = qwen_red.get("red_action", scenario["red_action"])
        red_desc = qwen_red.get("red_description", scenario["red_description"])
        target_file = qwen_red.get("target_file", scenario["target_file"])
        mutated_code = qwen_red.get("mutated_code", scenario["mutated_code"])
        expected_error = qwen_red.get("error_type", scenario["error_type"])
        mock_stderr = qwen_red.get("stderr", scenario["stderr"])
        tokens_red = qwen_red.get("token_cost_red", scenario["token_cost_red"])
    else:
        red_action = scenario["red_action"]
        red_desc = scenario["red_description"]
        target_file = scenario["target_file"]
        mutated_code = scenario["mutated_code"]
        expected_error = scenario["error_type"]
        mock_stderr = scenario["stderr"]
        tokens_red = scenario["token_cost_red"]

    env.total_ticks += 1
    env.token_budget_red = max(0, env.token_budget_red - tokens_red)
    
    tick_logs.append({
        "type": "red",
        "message": f"[RED ADVERSARY] Action: {red_action} on {target_file} | Cost: {tokens_red} tokens\n[RED ADVERSARY] Description: {red_desc}"
    })
    
    # Apply mutation to codebase
    original_code = env.codebase.files[target_file]
    env.codebase.files[target_file] = mutated_code
    loc_changed_red = env.calculate_loc_diff(original_code, mutated_code)

    # Sandbox execute
    sandbox_result = env.execute_codebase()
    system_down = not sandbox_result["success"]
    
    blue_patch_success = False
    tokens_blue = 0
    loc_changed_blue = 0
    blue_strategy = "N/A"
    blue_desc = "N/A"
    error_type = sandbox_result["error_type"] or "None"

    # Threads lock context for safety
    with env.lock:
        # Ingest RED action and FILE
        env.graph.add_node(red_action, type="red_mutation", weight=1.0)
        env.graph.add_node(target_file, type="code_file", weight=1.0)
        env.graph.add_edge(red_action, target_file, relationship="INJECTED_BY", weight=1.0)

    if system_down:
        tick_logs.append({
            "type": "judge",
            "message": f"[JUDGE DECISION] System crashed. Codebase offline. Trace: {error_type}"
        })
        
        with env.lock:
            # Ingest error node
            env.graph.add_node(error_type, type="error_trace", weight=1.0)
            env.graph.add_edge(target_file, error_type, relationship="CAUSED_ERROR", weight=1.0)

        # Trigger Blue mutation
        qwen_blue = get_qwen_mutation(client, env.codebase.files, "blue", history_ctx, error_trace=mock_stderr)
        
        if qwen_blue:
            blue_strategy = qwen_blue.get("blue_strategy", scenario["blue_strategy"])
            blue_desc = qwen_blue.get("blue_description", scenario["blue_description"])
            patched_code = qwen_blue.get("patched_code", scenario["patched_code"])
            tokens_blue = qwen_blue.get("token_cost_blue", scenario["token_cost_blue"])
        else:
            blue_strategy = scenario["blue_strategy"]
            blue_desc = scenario["blue_description"]
            patched_code = scenario["patched_code"]
            tokens_blue = scenario["token_cost_blue"]

        env.token_budget_blue = max(0, env.token_budget_blue - tokens_blue)
        tick_logs.append({
            "type": "blue",
            "message": f"[BLUE PATCHER] Strategy: {blue_strategy} on {target_file} | Cost: {tokens_blue} tokens\n[BLUE PATCHER] Description: {blue_desc}"
        })

        # Apply Patch
        pre_patch_code = env.codebase.files[target_file]
        env.codebase.files[target_file] = patched_code
        loc_changed_blue = env.calculate_loc_diff(pre_patch_code, patched_code)

        # Re-run codebase checks
        second_run = env.execute_codebase()
        if second_run["success"]:
            blue_patch_success = True
            env.uptime_ticks += 1
            tick_logs.append({
                "type": "judge",
                "message": "[JUDGE DECISION] Blue Patch successfully compiled. System back ONLINE."
            })
            
            with env.lock:
                # Ingest successful patch and edges
                env.graph.add_node(blue_strategy, type="blue_patch", weight=1.0)
                env.graph.add_edge(blue_strategy, error_type, relationship="FIXED_ERROR", weight=1.0)
                env.graph.add_edge(blue_strategy, target_file, relationship="PATCHED_FILE", weight=1.0)
                # Successful path gets reinforced weight
                env.graph.edges[blue_strategy, error_type]["weight"] = 1.0
                env.graph.edges[blue_strategy, target_file]["weight"] = 1.0
        else:
            tick_logs.append({
                "type": "judge",
                "message": f"[JUDGE DECISION] Blue Patch FAILED. System remains OFFLINE. New error: {second_run['error_type']}"
            })
            # Revert to mutated code to keep the error state for future ticks or mock sequences
            env.codebase.files[target_file] = pre_patch_code
            
            with env.lock:
                # Ingest failed patch (it will be aggressively pruned shortly)
                env.graph.add_node(blue_strategy, type="blue_patch", weight=0.1)
                env.graph.add_edge(blue_strategy, error_type, relationship="FAILED_FIX", weight=0.1)

    else:
        # System was not brought down (Red action immediately caught/ineffective)
        env.uptime_ticks += 1
        tick_logs.append({
            "type": "judge",
            "message": "[JUDGE DECISION] System operational. Red exploit was caught/ineffective. System remains ONLINE."
        })

    # Total LOC changed in tick
    total_loc_changed = loc_changed_red + loc_changed_blue

    # Apply Synaptic Decay and Aggressive Pruning
    # Prune rule: If Blue patch fails, remove its node/edges. If Red exploit immediately caught, prune it.
    with env.lock:
        apply_synaptic_decay_and_pruning(env.graph, decay_rate, time_delta=1.0, 
                                         blue_failed=(system_down and not blue_patch_success),
                                         failed_patch_node=blue_strategy,
                                         red_caught=(not system_down),
                                         caught_exploit_node=red_action)

    # Increment scenario index
    env.scenario_index += 1

    judge_summary = {
        "tick": env.total_ticks,
        "uptime": env.get_uptime_percentage(),
        "tokens_red": env.token_budget_red,
        "tokens_blue": env.token_budget_blue,
        "loc_changed": total_loc_changed,
        "active_nodes": len(env.graph.nodes),
        "active_edges": len(env.graph.edges),
        "logs": tick_logs
    }
    
    return judge_summary

def apply_synaptic_decay_and_pruning(graph: nx.DiGraph, decay_rate: float, time_delta: float, 
                                     blue_failed: bool = False, failed_patch_node: str = "",
                                     red_caught: bool = False, caught_exploit_node: str = "",
                                     threshold: float = None):
    """
    Decays edge and node weights.
    Aggressively prunes failed patch strategies or caught exploits immediately.
    """
    if threshold is None:
        try:
            threshold = float(os.environ.get("SYNAPTIC_DECAY_FLOOR", "0.1"))
        except ValueError:
            threshold = 0.1
    # 1. Aggressive Pruning of failed patch
    if blue_failed and failed_patch_node in graph:
        print(f"[NSDKG PRUNING] Aggressive Pruning: Blue patch '{failed_patch_node}' failed. Removing node and associated edges.")
        graph.remove_node(failed_patch_node)

    # 2. Aggressive Pruning of caught exploit
    if red_caught and caught_exploit_node in graph:
        print(f"[NSDKG PRUNING] Aggressive Pruning: Red exploit '{caught_exploit_node}' immediately caught. Removing node.")
        graph.remove_node(caught_exploit_node)

    # 3. Standard Temporal Decay
    edges_to_remove = []
    for u, v, data in graph.edges(data=True):
        old_w = data.get("weight", 1.0)
        new_w = old_w * math.exp(-decay_rate * time_delta)
        data["weight"] = new_w
        if new_w < threshold:
            edges_to_remove.append((u, v))

    for u, v in edges_to_remove:
        print(f"[NSDKG DECAY] Pruned decayed edge: [{u}] -> [{v}]")
        graph.remove_edge(u, v)

    nodes_to_remove = []
    for node, data in graph.nodes(data=True):
        old_w = data.get("weight", 1.0)
        new_w = old_w * math.exp(-decay_rate * time_delta)
        data["weight"] = new_w
        
        # Check active dependency
        if new_w < threshold:
            # Check if isolated (degree = 0)
            if graph.degree(node) == 0:
                nodes_to_remove.append(node)

    for node in nodes_to_remove:
        print(f"[NSDKG DECAY] Pruned decayed isolated node: [{node}]")
        graph.remove_node(node)

def get_compressed_history(env: ColosseumSandboxEnv) -> str:
    """
    Gathers top-performing subgraphs from the NetworkX graph and serializes 
    them into a highly dense semantic text string under 100 tokens.
    """
    with env.lock:
        if not env.graph or len(env.graph.edges) == 0:
            return "No active execution memory."
        
        # Sort edges by weight descending
        sorted_edges = sorted(env.graph.edges(data=True), key=lambda x: x[2].get("weight", 1.0), reverse=True)
        
        paths = []
        for u, v, data in sorted_edges:
            weight = data.get("weight", 1.0)
            rel = data.get("relationship", "LINK")
            paths.append(f"[{u}]-{rel}->[{v}]({weight:.2f})")
            
        # Join pathways
        serialized = " | ".join(paths)
        
        # Enforce sub-100 token constraint (approx 400 characters)
        if len(serialized) > 400:
            serialized = serialized[:397] + "..."
            
        return serialized

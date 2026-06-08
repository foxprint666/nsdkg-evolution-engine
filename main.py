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
import time
from nsdkg import NSDatabase, validate_and_ingest_pathway, apply_temporal_decay, run_sandboxed, EvolutionAgent
from deploy.alibaba_ecs_config import AliyunComputeCluster

def extract_error_summary(stderr: str) -> str:
    """Extracts the core exception type from standard error logs."""
    if "TimeoutError" in stderr or "TimeoutExpired" in stderr:
        return "TimeoutError"
    if "SyntaxError" in stderr:
        return "SyntaxError"
    lines = stderr.strip().split("\n")
    if lines:
        last_line = lines[-1]
        # E.g. "TypeError: unsupported operand..."
        if ":" in last_line:
            return last_line.split(":")[0].strip()
    return "UnknownException"

def main():
    print("=========================================================")
    print("      NSDKG Evolution Engine - Initialization Sequence   ")
    print("=========================================================")
    
    # 1. Initialize Active Graph Core
    db = NSDatabase()
    
    # 2. Initialize Cognitive Brain
    agent = EvolutionAgent()
    
    # 3. Simulate an initial failure ingested into the graph
    print("\n[SYSTEM] Simulating historical failures to populate knowledge graph...")
    validate_and_ingest_pathway(db.graph, "Initial_Mutation", "While_Loop", "TimeoutError")
    validate_and_ingest_pathway(db.graph, "Syntax_Fix_1", "Parsing_Logic", "SyntaxError")
    
    # 4. Evolution Loop Execution
    session_loops = 3
    lambda_val = 0.5  # Decay rate
    
    task_benchmark = "Write a simple function 'add(a, b)' that returns the sum of a and b. Include a test block."
    
    for i in range(session_loops):
        print(f"\n==================== GA GENERATION {i+1} ====================")
        
        # Propose code mutation
        code_mutation = agent.propose_mutation(db, task_benchmark)
        if not code_mutation:
            print("[SYSTEM] No code mutation generated. Halting loop.")
            break
            
        # Write mutation to sandbox target
        target_file = "sandbox_target.py"
        with open(target_file, "w") as f:
            f.write(code_mutation)
            
        # Execute sandboxed mutation
        result = run_sandboxed(target_file, timeout_sec=3.0)
        
        if not result["success"]:
            # Process failure
            error_type = extract_error_summary(result["stderr"])
            print(f"[SYSTEM] Task Failed. Encountered: {error_type}")
            
            # Extract basic feature usage representation (e.g., function names)
            used_feature = "unknown_feature"
            if "def " in code_mutation:
                used_feature = code_mutation.split("def ")[1].split("(")[0].strip()
                
            validate_and_ingest_pathway(db.graph, f"Gen_{i+1}_Mutation", used_feature, error_type)
        else:
            print("[SYSTEM] Task Succeeded!")
            print(result["stdout"])
            
        # Apply synaptic decay at the end of the session loop
        apply_temporal_decay(db.graph, lambda_val, time_delta=1.0, threshold=0.1)
        
        # Small delay for pacing
        time.sleep(1)
        
    print("\n==================== EVOLUTION COMPLETE ====================")
    print("Final compressed memory string for next loop:")
    print(db.get_compressed_history())
    
    # Clean up temp file
    if os.path.exists("sandbox_target.py"):
        os.remove("sandbox_target.py")

if __name__ == "__main__":
    main()

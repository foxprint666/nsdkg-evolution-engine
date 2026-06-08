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
from openai import OpenAI
from .graph_memory import NSDatabase

SYSTEM_PROMPT = """You are an expert systems engineer specializing in autonomous agent architectures, graph 
data structures, and Alibaba Cloud deployments. Please write a production-ready Python 
framework combining a Track 4 Genetic Algorithm code-mutation framework with a Track 1 
Neuro-Synaptic Decaying Knowledge Graph (NSDKG) using NetworkX.

The application must include:
1. An isolated sandbox execution loop using the subprocess module with explicit CPU 
   timeout enforcement to execute code mutations against standard unit tests.
2. A graph ingestion engine using regular expressions or an LLM parser to compress stack 
   traces into atomic node pathways: [Mutation] -> [Used Feature] ->.
3. A localized mathematical exponential decay mechanism running at the end of each session 
   loop according to the formula W_new = W_old * e^(-lambdat), pruning any nodes whose 
   weight falls below a hard floor of 0.1.
4. An OpenAI SDK integration configured to talk natively to the Qwen Cloud API Base URL, 
   loading compressed, sub-100 token historical memory paths directly into the system context.

Ensure code is modular, includes robust error handling, produces structural console logs 
for system tracking, and includes an open-source MIT license header block."""

class EvolutionAgent:
    def __init__(self, model_name="qwen3.7-max"):
        self.model_name = model_name
        
        # Load local .env if it exists and variables aren't already set in environment
        env_paths = [
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        ]
        for path in env_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                k = k.strip()
                                if k not in os.environ:
                                    os.environ[k] = v.strip()
                    break
                except Exception:
                    pass

        api_key = os.environ.get("QWEN_API_KEY", "dummy-key-for-local-testing")
        base_url = os.environ.get("DASHSCOPE_BASE_URL") or os.environ.get("QWEN_BASE_URL") or "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        
        # Configure OpenAI SDK for Qwen API
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        print(f"[COGNITIVE CORE] Initialized Qwen Evolution Agent (Model: {self.model_name})")

    def propose_mutation(self, graph_memory: NSDatabase, task_benchmark: str) -> str:
        """
        Queries the LLM with the compressed graph memory footprint.
        Uses preserve_thinking parameters if available for advanced reasoning.
        """
        # Retrieve sub-100 token path history
        compressed_memory = graph_memory.get_compressed_history()
        
        prompt = f"Historical Execution Context (Graph Path):\n{compressed_memory}\n\nCurrent Task Benchmark:\n{task_benchmark}\n\nProvide the Python code mutation to solve this. Only return code."
        
        print("[COGNITIVE CORE] Dispatching prompt to Qwen API...")
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                # Additional Qwen compatible parameters like 'preserve_thinking' can be passed in extra_body
                extra_body={"preserve_thinking": True}
            )
            mutation_code = response.choices[0].message.content
            print("[COGNITIVE CORE] Mutation received.")
            
            # Simple parser to extract code blocks if needed
            code_match = re.search(r'```python(.*?)```', mutation_code, re.DOTALL)
            if code_match:
                return code_match.group(1).strip()
            return mutation_code.strip()
            
        except Exception as e:
            print(f"[COGNITIVE CORE ERROR] API Request failed: {str(e)}")
            # Return a fallback or empty mutation
            return ""

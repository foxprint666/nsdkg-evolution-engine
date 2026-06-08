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

import math
import networkx as nx

# Validation schema for extracted exceptions
VALID_EXCEPTION_TOKENS = {
    "TimeoutError", "SyntaxError", "MemoryLeak", 
    "TypeError", "NameError", "AttributeError",
    "ModuleNotFoundError", "IndexError", "KeyError"
}

class NSDatabase:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.session_time = 0
        print("[NSDKG] Graph Memory Initialized.")

    def get_compressed_history(self) -> str:
        """Serializes the remaining high-weight paths into a sub-100 token representation."""
        # Simple edge list representation
        edges = []
        for u, v, data in self.graph.edges(data=True):
            edges.append(f"[{u}]->[{v}]({data.get('weight', 1.0):.2f})")
        
        path_str = " | ".join(edges)
        
        # Simple token tracking (approximate)
        approx_tokens = len(path_str) // 4
        print(f"[NSDKG] Graph state serialized. Active Edges: {len(self.graph.edges())}, Approx Tokens: {approx_tokens}")
        return path_str

def validate_and_ingest_pathway(graph: nx.DiGraph, mutation: str, feature: str, extracted_error: str):
    """Parses and ingests failure pathways avoiding hallucinatory graph expansion."""
    standardized_error = "UnknownException"
    for exception in VALID_EXCEPTION_TOKENS:
        if exception.lower() in extracted_error.lower():
            standardized_error = exception
            break
            
    if standardized_error == "UnknownException":
        print(f"[NSDKG INGESTION] Discarded hallucinatory pathway: {extracted_error}")
        return
        
    print(f"[NSDKG INGESTION] Ingested verified pathway: [{mutation}] -> [{feature}] -> [{standardized_error}]")
    graph.add_edge(mutation, feature, weight=1.0)
    graph.add_edge(feature, standardized_error, weight=1.0)
    
    # Initialize node attributes
    if mutation not in graph.nodes:
        graph.nodes[mutation]['is_immutable'] = False
    if feature not in graph.nodes:
        graph.nodes[feature]['is_immutable'] = False
    if standardized_error not in graph.nodes:
        graph.nodes[standardized_error]['is_immutable'] = True # Standard errors don't decay away

def has_active_dependency(graph: nx.DiGraph, node: str, threshold: float) -> bool:
    """Check if node is connected to any active paths."""
    for neighbor in graph.neighbors(node):
        if graph.edges[node, neighbor].get('weight', 0) >= threshold:
            return True
    for predecessor in graph.predecessors(node):
        if graph.edges[predecessor, node].get('weight', 0) >= threshold:
            return True
    return False

def apply_temporal_decay(graph: nx.DiGraph, lambda_val: float, time_delta: float, threshold: float = 0.1):
    """
    Simulates biological forgetting by decaying edge and node weights.
    Prunes nodes that fall below the threshold unless they are immutable or have active neighbors.
    """
    print(f"\n--- [NSDKG SYNAPTIC DECAY] Running Decay Cycle (lambda={lambda_val}, t_delta={time_delta}) ---")
    nodes_to_prune = []
    edges_to_prune = []
    
    # Decay edges
    for u, v, data in graph.edges(data=True):
        old_weight = data.get('weight', 1.0)
        new_weight = old_weight * math.exp(-lambda_val * time_delta)
        data['weight'] = new_weight
        if new_weight < threshold:
            edges_to_prune.append((u, v))
            
    # Remove decayed edges
    for u, v in edges_to_prune:
        print(f"[NSDKG DECAY] Pruned edge [{u}] -> [{v}] (Weight decayed below {threshold})")
        graph.remove_edge(u, v)

    # Decay nodes and check neighborhood
    for node, data in graph.nodes(data=True):
        if data.get("is_immutable", False):
            # Bypass decay calculation entirely
            continue
            
        old_weight = data.get("weight", 1.0)
        new_weight = old_weight * math.exp(-lambda_val * time_delta)
        data["weight"] = new_weight
        
        if new_weight < threshold:
            if not has_active_dependency(graph, node, threshold):
                nodes_to_prune.append(node)
                
    for node in nodes_to_prune:
        print(f"[NSDKG DECAY] Pruned isolated node [{node}]")
        graph.remove_node(node)

    print(f"--- [NSDKG SYNAPTIC DECAY] Cycle Complete. Active Nodes: {len(graph.nodes())} ---\n")

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
import sys
import time
import threading
import webbrowser
from flask import Flask, jsonify, render_template_string
from openai import OpenAI
from nsdkg.colosseum import ColosseumSandboxEnv, colosseum_simulation_tick, get_compressed_history

app = Flask(__name__)

# Global environment instance
env = ColosseumSandboxEnv()

# Initialize Qwen client using the same environment configuration
api_key = os.environ.get("QWEN_API_KEY")
base_url = os.environ.get("DASHSCOPE_BASE_URL") or os.environ.get("QWEN_BASE_URL") or "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

client = None
if api_key and "dummy" not in api_key:
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        print(f"[SYSTEM] OpenAI Client configured for Qwen Cloud API: {base_url}")
    except Exception as e:
        print(f"[SYSTEM WARNING] Failed to initialize Qwen Cloud API client: {str(e)}")

# Background simulator thread function
def run_simulation_loop():
    # Pre-populate graph memory with historical failure pathway nodes and edges to make it look good initially
    with env.lock:
        env.graph.add_node("Inject_DivZero", type="red_mutation", weight=0.8)
        env.graph.add_node("auth.py", type="code_file", weight=1.0)
        env.graph.add_edge("Inject_DivZero", "auth.py", relationship="INJECTED_BY", weight=0.85)
        
        env.graph.add_node("ZeroDivisionError", type="error_trace", weight=0.8)
        env.graph.add_edge("auth.py", "ZeroDivisionError", relationship="CAUSED_ERROR", weight=0.8)
        
        env.graph.add_node("SafeLimitCheck", type="blue_patch", weight=0.95)
        env.graph.add_edge("SafeLimitCheck", "ZeroDivisionError", relationship="FIXED_ERROR", weight=0.95)
        env.graph.add_edge("SafeLimitCheck", "auth.py", relationship="PATCHED_FILE", weight=0.9)

    env.history_logs.append({
        "type": "judge",
        "message": "[SYSTEM] Simulated codebase repository initialized with modules: auth.py, db.py, app_logic.py"
    })
    env.history_logs.append({
        "type": "judge",
        "message": "[SYSTEM] Historical failure pathways successfully ingested into NSDKG memory."
    })

    print("[SYSTEM] Cyber-Colosseum simulation loop started in background thread.")
    while True:
        try:
            # Tick every 4 seconds to pace the visual logs nicely
            time.sleep(4.0)
            
            # Execute simulation tick
            tick_summary = colosseum_simulation_tick(env, client=client, decay_rate=0.15)
            
            # Print state details to terminal
            print(f"[TICK {tick_summary['tick']}] Uptime: {tick_summary['uptime']:.2f}% | Active Nodes: {tick_summary['active_nodes']} | Edges: {tick_summary['active_edges']}")
            
            # Transfer simulation logs to global history
            for log in tick_summary["logs"]:
                env.history_logs.append(log)
                
            # Truncate logs if they get too long to prevent client load lag
            if len(env.history_logs) > 100:
                env.history_logs = env.history_logs[-100:]
                
        except Exception as e:
            print(f"[SIMULATOR ERROR] Error during colosseum tick: {str(e)}")

# Starting simulation thread as a daemon thread
sim_thread = threading.Thread(target=run_simulation_loop, daemon=True)
sim_thread.start()

# HTML page template served natively
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NSDKG Cyber-Colosseum Monitor</title>
    <!-- Google Typography -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <!-- Vis.js library -->
    <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/vis-network.min.js"></script>
    <script type="text/javascript">
        if (typeof vis === 'undefined') {
            document.write('<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"><\\/script>');
        }
    </script>
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: #141b2d;
            --border-color: #232d45;
            --text-color: #f1f5f9;
            --text-muted: #94a3b8;
            --red-glow: rgba(239, 68, 68, 0.15);
            --blue-glow: rgba(59, 130, 246, 0.15);
            --purple-glow: rgba(168, 85, 247, 0.15);
            
            --red-border: #7f1d1d;
            --red-bg: #451a1a;
            --red-text: #fca5a5;

            --blue-border: #1e3a8a;
            --blue-bg: #172554;
            --blue-text: #93c5fd;

            --judge-border: #78350f;
            --judge-bg: #3f2f1a;
            --judge-text: #fde047;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        header {
            background-color: var(--card-bg);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
        }

        .header-title {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .header-title h1 {
            font-size: 1.25rem;
            font-weight: 600;
            background: linear-gradient(135deg, #a855f7, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .status-badge {
            background-color: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }

        .status-badge::before {
            content: "";
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #10b981;
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.9); opacity: 1; }
            50% { transform: scale(1.3); opacity: 0.4; }
            100% { transform: scale(0.9); opacity: 1; }
        }

        .main-container {
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            flex: 1;
            height: calc(100vh - 65px);
            overflow: hidden;
        }

        .column-left {
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            padding: 1.5rem;
            gap: 1.5rem;
            overflow: hidden;
            background-color: rgba(11, 15, 25, 0.5);
        }

        .column-right {
            display: flex;
            flex-direction: column;
            padding: 1.5rem;
            gap: 1.5rem;
            overflow: hidden;
        }

        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .section-header h2 {
            font-size: 1rem;
            font-weight: 500;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Status Grid */
        .status-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
        }

        .status-card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            padding: 1rem 1.25rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }

        .status-card::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
        }

        .status-card.uptime::after { background-color: #10b981; }
        .status-card.red-budget::after { background-color: #ef4444; }
        .status-card.blue-budget::after { background-color: #3b82f6; }
        .status-card.graph-stats::after { background-color: #a855f7; }

        .status-card .card-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            font-weight: 500;
            margin-bottom: 0.5rem;
        }

        .status-card .card-value {
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.025em;
        }

        /* Terminal Logs style */
        .terminal-container {
            flex: 1;
            background-color: #070913;
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06);
        }

        .terminal-header {
            background-color: #101424;
            border-bottom: 1px solid var(--border-color);
            padding: 0.5rem 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .terminal-dots {
            display: flex;
            gap: 0.35rem;
        }

        .terminal-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        .terminal-dot.red { background-color: #ef4444; }
        .terminal-dot.yellow { background-color: #f59e0b; }
        .terminal-dot.green { background-color: #10b981; }

        .terminal-title {
            font-size: 0.7rem;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-muted);
        }

        .terminal-body {
            flex: 1;
            padding: 1rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            line-height: 1.4;
        }

        .log-entry {
            border-radius: 0.375rem;
            padding: 0.5rem 0.75rem;
            border-left: 3px solid transparent;
            animation: fadeIn 0.25s ease-out;
            white-space: pre-wrap;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .log-entry.red {
            background-color: var(--red-bg);
            border-color: var(--red-border);
            color: var(--red-text);
        }

        .log-entry.blue {
            background-color: var(--blue-bg);
            border-color: var(--blue-border);
            color: var(--blue-text);
        }

        .log-entry.judge {
            background-color: var(--judge-bg);
            border-color: var(--judge-border);
            color: var(--judge-text);
        }

        /* NSDKG Graph Area */
        .graph-container {
            flex: 1;
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        #network-graph {
            width: 100%;
            height: 100%;
        }

        .graph-legend {
            position: absolute;
            bottom: 1rem;
            left: 1rem;
            background-color: rgba(11, 15, 25, 0.85);
            border: 1px solid var(--border-color);
            padding: 0.75rem;
            border-radius: 0.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            z-index: 5;
            font-size: 0.7rem;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .legend-color {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }

        /* History Compression bar */
        .history-compression-card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            padding: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .compression-title {
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .compression-content {
            background-color: #070913;
            border: 1px solid var(--border-color);
            border-radius: 0.375rem;
            padding: 0.5rem 0.75rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: #a855f7;
            word-break: break-all;
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }

        ::-webkit-scrollbar-track {
            background: transparent;
        }

        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-muted);
        }
    </style>
</head>
<body>

    <header>
        <div class="header-title">
            <h1>NSDKG Cyber-Colosseum Engine</h1>
            <span class="status-badge">Active Simulator</span>
        </div>
        <div style="font-size: 0.75rem; color: var(--text-muted);">
            Local Host Server Loop: Ticks Active
        </div>
    </header>

    <div class="main-container">
        
        <!-- Column 1: Colosseum Monitor -->
        <div class="column-left">
            <div class="section-header">
                <h2>Colosseum Monitor</h2>
            </div>
            
            <div class="status-grid">
                <div class="status-card uptime">
                    <span class="card-label">CODEBASE UPTIME</span>
                    <span class="card-value" id="uptime-val">100.0%</span>
                </div>
                <div class="status-card graph-stats">
                    <span class="card-label">NSDKG ELEMENT COUNT</span>
                    <span class="card-value" id="elements-val">0 Nodes</span>
                </div>
                <div class="status-card red-budget">
                    <span class="card-label">RED BUDGET (TOKENS)</span>
                    <span class="card-value" id="red-tokens-val">100,000</span>
                </div>
                <div class="status-card blue-budget">
                    <span class="card-label">BLUE BUDGET (TOKENS)</span>
                    <span class="card-value" id="blue-tokens-val">100,000</span>
                </div>
            </div>

            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-dots">
                        <div class="terminal-dot red"></div>
                        <div class="terminal-dot yellow"></div>
                        <div class="terminal-dot green"></div>
                    </div>
                    <div class="terminal-title">colosseum_stdout_stderr.log</div>
                    <div></div>
                </div>
                <div class="terminal-body" id="logs-container">
                    <!-- Logs stream in here -->
                </div>
            </div>
        </div>

        <!-- Column 2: Interactive NSDKG Graph Viewer -->
        <div class="column-right">
            <div class="section-header">
                <h2>Interactive NSDKG Graph Viewer</h2>
            </div>

            <div class="graph-container">
                <div id="network-graph"></div>
                
                <div class="graph-legend">
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #ef4444;"></div>
                        <span>Red Mutation (Exploit)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #3b82f6;"></div>
                        <span>Blue Patch (Strategy)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #a855f7;"></div>
                        <span>Error Trace</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #10b981;"></div>
                        <span>Code File Target</span>
                    </div>
                </div>
            </div>

            <div class="history-compression-card">
                <div class="compression-title">Evolution Feedback (Sub-100 Token compressed footprint)</div>
                <div class="compression-content" id="compression-val">Loading NSDKG serialized state...</div>
            </div>
        </div>

    </div>

    <script>
        let network = null;
        let nodesDataSet = null;
        let edgesDataSet = null;
        let lastLogsCount = 0;

        // Initialize Vis Graph
        function initGraph() {
            if (typeof vis === 'undefined') {
                console.warn("Vis.js is not loaded. Graph visualization disabled.");
                const container = document.getElementById('network-graph');
                container.innerHTML = `<div style="padding: 2rem; color: #ef4444; font-family: sans-serif; text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                    <strong style="margin-bottom: 0.5rem; font-size: 1.1rem;">Visualization Offline</strong>
                    <span style="font-size: 0.85rem; color: var(--text-muted); max-width: 320px; line-height: 1.4;">Failed to load Vis.js library from online CDNs. Terminal logs and system metrics will continue to function normally.</span>
                </div>`;
                return;
            }
            nodesDataSet = new vis.DataSet([]);
            edgesDataSet = new vis.DataSet([]);
            const container = document.getElementById('network-graph');
            const data = {
                nodes: nodesDataSet,
                edges: edgesDataSet
            };
            const options = {
                physics: {
                    stabilization: false,
                    barnesHut: {
                        gravitationalConstant: -2000,
                        centralGravity: 0.15,
                        springLength: 120,
                        springConstant: 0.04,
                        damping: 0.09,
                        avoidOverlap: 0.5
                    }
                },
                nodes: {
                    shape: 'dot',
                    font: {
                        color: '#ffffff',
                        size: 11,
                        face: 'Inter',
                        strokeWidth: 2,
                        strokeColor: '#0b0f19'
                    },
                    borderWidth: 2,
                    shadow: {
                        enabled: true,
                        color: 'rgba(0,0,0,0.5)',
                        size: 5
                    }
                },
                edges: {
                    arrows: {
                        to: { enabled: true, scaleFactor: 0.8 }
                    },
                    font: {
                        color: '#64748b',
                        size: 9,
                        face: 'Inter',
                        align: 'top'
                    },
                    color: {
                        color: '#2d3748',
                        highlight: '#6366f1',
                        hover: '#6366f1'
                    },
                    width: 2,
                    shadow: {
                        enabled: true,
                        color: 'rgba(0,0,0,0.3)',
                        size: 3
                    }
                }
            };
            network = new vis.Network(container, data, options);
        }

        // Returns color matching the node type
        function getNodeColor(type) {
            switch(type) {
                case 'red_mutation': return { background: '#ef4444', border: '#b91c1c', highlight: '#f87171' };
                case 'blue_patch': return { background: '#3b82f6', border: '#1d4ed8', highlight: '#60a5fa' };
                case 'error_trace': return { background: '#a855f7', border: '#7e22ce', highlight: '#c084fc' };
                case 'code_file': return { background: '#10b981', border: '#047857', highlight: '#34d399' };
                default: return { background: '#64748b', border: '#475569', highlight: '#94a3b8' };
            }
        }

        // Poll API to update dashboard
        async function fetchSystemState() {
            try {
                const response = await fetch('/api/state');
                const state = await response.json();

                // Update Metrics Card
                document.getElementById('uptime-val').innerText = state.uptime.toFixed(1) + '%';
                document.getElementById('elements-val').innerText = `${state.active_nodes_count} Nodes, ${state.active_edges_count} Edges`;
                document.getElementById('red-tokens-val').innerText = state.tokens_red.toLocaleString();
                document.getElementById('blue-tokens-val').innerText = state.tokens_blue.toLocaleString();
                document.getElementById('compression-val').innerText = state.compressed_history;

                // Sync Logs
                const logsContainer = document.getElementById('logs-container');
                if (state.logs.length > lastLogsCount) {
                    for (let i = lastLogsCount; i < state.logs.length; i++) {
                        const log = state.logs[i];
                        const logDiv = document.createElement('div');
                        logDiv.className = `log-entry ${log.type}`;
                        logDiv.innerText = log.message;
                        logsContainer.appendChild(logDiv);
                    }
                    lastLogsCount = state.logs.length;
                    logsContainer.scrollTop = logsContainer.scrollHeight;
                }

                // Sync Graph Nodes & Edges only if Vis.js loaded successfully
                if (nodesDataSet && edgesDataSet) {
                    const currentNodes = nodesDataSet.get();
                    const newNodesMap = new Map();
                    
                    state.graph.nodes.forEach(node => {
                        newNodesMap.set(node.id, node);
                        const size = Math.max(12, Math.min(35, 12 + (node.weight * 20))); // scale node size by decay weight
                        const colors = getNodeColor(node.type);
                        
                        if (nodesDataSet.get(node.id)) {
                            // Update
                            nodesDataSet.update({
                                id: node.id,
                                size: size,
                                color: colors
                            });
                        } else {
                            // Insert
                            nodesDataSet.add({
                                id: node.id,
                                label: node.id,
                                size: size,
                                color: colors,
                                title: `Type: ${node.type} | Weight: ${node.weight.toFixed(2)}`
                            });
                        }
                    });

                    // Remove nodes that are no longer present in graph (pruned / decayed)
                    currentNodes.forEach(oldNode => {
                        if (!newNodesMap.has(oldNode.id)) {
                            nodesDataSet.remove(oldNode.id);
                        }
                    });

                    // Sync Graph Edges
                    const currentEdges = edgesDataSet.get();
                    const newEdgesMap = new Map();

                    state.graph.edges.forEach(edge => {
                        const edgeId = `${edge.from}-${edge.to}`;
                        newEdgesMap.set(edgeId, edge);
                        
                        // Edge opacity represented by width/color intensity
                        const edgeWidth = Math.max(1, Math.min(8, 1 + (edge.weight * 6)));
                        
                        if (edgesDataSet.get(edgeId)) {
                            edgesDataSet.update({
                                id: edgeId,
                                width: edgeWidth,
                                label: edge.relationship
                            });
                        } else {
                            edgesDataSet.add({
                                id: edgeId,
                                from: edge.from,
                                to: edge.to,
                                label: edge.relationship,
                                width: edgeWidth
                            });
                        }
                    });

                    // Remove edges that are no longer present
                    currentEdges.forEach(oldEdge => {
                        const edgeId = `${oldEdge.from}-${oldEdge.to}`;
                        if (!newEdgesMap.has(edgeId)) {
                            edgesDataSet.remove(oldEdge.id);
                        }
                    });
                }

            } catch (err) {
                console.error("Error fetching state api:", err);
            }
        }

        window.onload = () => {
            initGraph();
            fetchSystemState();
            // Fetch every 1.5 seconds to refresh logs and graphs smoothly
            setInterval(fetchSystemState, 1500);
        };
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/state")
def get_state():
    # Thread-locked read operations to prevent concurrent modification exceptions from background runner
    with env.lock:
        nodes = []
        for node_id, data in env.graph.nodes(data=True):
            nodes.append({
                "id": node_id,
                "type": data.get("type", "unknown"),
                "weight": data.get("weight", 1.0)
            })
            
        edges = []
        for u, v, data in env.graph.edges(data=True):
            edges.append({
                "from": u,
                "to": v,
                "relationship": data.get("relationship", "LINK"),
                "weight": data.get("weight", 1.0)
            })

    compressed = get_compressed_history(env)

    return jsonify({
        "uptime": env.get_uptime_percentage(),
        "tokens_red": env.token_budget_red,
        "tokens_blue": env.token_budget_blue,
        "active_nodes_count": len(nodes),
        "active_edges_count": len(edges),
        "logs": env.history_logs,
        "graph": {
            "nodes": nodes,
            "edges": edges
        },
        "compressed_history": compressed
    })

def main():
    # Open local browser window after 1.5 seconds delay to allow server initialization
    def open_browser():
        time.sleep(1.5)
        # Avoid opening browser automatically if running in non-interactive environment (e.g. background task runner)
        if os.environ.get("NO_BROWSER") or not sys.stdin or not sys.stdin.isatty():
            print("[SYSTEM] Non-interactive environment detected. Skipping auto-browser launch.")
            return
        url = "http://127.0.0.1:5000"
        print(f"[SYSTEM] Launching default web browser targeting: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"[SYSTEM WARNING] Failed to open browser automatically: {e}")

    browser_thread = threading.Thread(target=open_browser)
    browser_thread.start()

    print("=========================================================")
    print("      NSDKG Cyber-Colosseum Engine - Dashboard Server   ")
    print("=========================================================")
    print("[SYSTEM] Starting Flask development server...")
    
    # Run server locally on port 5000, disabling debugger when threads are active
    app.run(host="127.0.0.1", port=5000, debug=False)

if __name__ == "__main__":
    main()

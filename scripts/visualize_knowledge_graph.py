#!/usr/bin/env python3
"""
Visualize Ira's Knowledge Graph

Creates interactive HTML visualization of the knowledge graph
showing nodes, relationships, and clusters.

Usage:
    python scripts/visualize_knowledge_graph.py
    
    Then open data/knowledge/knowledge_graph.html in browser
"""

import json
import os
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"
GRAPH_FILE = KNOWLEDGE_DIR / "knowledge_graph.json"
CLUSTERS_FILE = KNOWLEDGE_DIR / "clusters.json"
OUTPUT_HTML = KNOWLEDGE_DIR / "knowledge_graph_visualization.html"


def load_graph_data():
    """Load knowledge graph data."""
    nodes = {}
    edges = []
    clusters = []
    
    if GRAPH_FILE.exists():
        data = json.loads(GRAPH_FILE.read_text())
        nodes = data.get('nodes', {})
        edges = data.get('edges', [])
    
    if CLUSTERS_FILE.exists():
        clusters_data = json.loads(CLUSTERS_FILE.read_text())
        if isinstance(clusters_data, list):
            clusters = clusters_data
        elif isinstance(clusters_data, dict):
            inner = clusters_data.get('clusters', clusters_data)
            if isinstance(inner, list):
                clusters = inner
            elif isinstance(inner, dict):
                clusters = list(inner.values())
    
    return nodes, edges, clusters


def generate_graph_stats(nodes, edges, clusters):
    """Generate statistics about the knowledge graph."""
    stats = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "total_clusters": len(clusters),
    }
    
    # Node types
    if isinstance(nodes, dict):
        node_types = Counter(n.get('knowledge_type', 'unknown') for n in nodes.values())
        stats["node_types"] = dict(node_types)
    
    # Relationship types
    rel_types = Counter(e.get('relationship_type', 'unknown') for e in edges)
    stats["relationship_types"] = dict(rel_types)
    
    # Entities
    if isinstance(nodes, dict):
        entities = Counter(n.get('entity', 'unknown') for n in nodes.values())
        stats["top_entities"] = dict(entities.most_common(20))
    
    return stats


def generate_vis_js_html(nodes, edges, clusters, stats):
    """Generate interactive visualization using vis.js."""
    
    # Prepare nodes for vis.js
    vis_nodes = []
    node_colors = {
        "machine_spec": "#4CAF50",      # Green
        "commercial": "#2196F3",         # Blue
        "operational": "#FF9800",        # Orange
        "application": "#9C27B0",        # Purple
        "market_intelligence": "#E91E63", # Pink
        "lead": "#00BCD4",               # Cyan
        "client": "#FFEB3B",             # Yellow
        "case_study": "#795548",         # Brown
        "general": "#607D8B",            # Gray
    }
    
    node_id_map = {}
    for idx, (nid, node) in enumerate(nodes.items() if isinstance(nodes, dict) else []):
        ktype = node.get('knowledge_type', 'general')
        entity = node.get('entity', '')[:30]
        source = node.get('source_file', '')[:20]
        
        vis_nodes.append({
            "id": idx,
            "label": entity or f"Node {idx}",
            "title": f"{entity}\n[{ktype}]\n{source}",
            "color": node_colors.get(ktype, "#607D8B"),
            "group": ktype,
        })
        node_id_map[nid] = idx
    
    # Prepare edges for vis.js (sample to avoid overwhelming browser)
    vis_edges = []
    edge_colors = {
        "same_entity": "#4CAF50",
        "same_source": "#9E9E9E",
        "same_model_family": "#2196F3",
        "same_cluster": "#FF9800",
        "application_overlap": "#9C27B0",
        "similar_content": "#00BCD4",
    }
    
    # Sample edges if too many
    sampled_edges = edges[:2000] if len(edges) > 2000 else edges
    
    for edge in sampled_edges:
        source = edge.get('source_id', '')
        target = edge.get('target_id', '')
        rel_type = edge.get('relationship_type', 'unknown')
        
        if source in node_id_map and target in node_id_map:
            vis_edges.append({
                "from": node_id_map[source],
                "to": node_id_map[target],
                "title": rel_type,
                "color": {"color": edge_colors.get(rel_type, "#BDBDBD")},
            })
    
    # Generate HTML
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Ira Knowledge Graph Visualization</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #1a1a2e;
            color: #eee;
        }}
        h1 {{
            color: #00d4ff;
            margin-bottom: 10px;
        }}
        .container {{
            display: flex;
            gap: 20px;
        }}
        #graph {{
            width: 70%;
            height: 700px;
            border: 2px solid #333;
            border-radius: 8px;
            background: #16213e;
        }}
        .stats {{
            width: 28%;
            background: #16213e;
            padding: 20px;
            border-radius: 8px;
            border: 2px solid #333;
        }}
        .stat-card {{
            background: #1a1a2e;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            color: #00d4ff;
            font-size: 14px;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: bold;
            color: #4CAF50;
        }}
        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 12px;
        }}
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}
        ul {{
            padding-left: 20px;
            margin: 0;
        }}
        li {{
            margin: 5px 0;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <h1>🧠 Ira Knowledge Graph</h1>
    <p style="color: #888; margin-bottom: 20px;">Interactive visualization of Machinecraft & Thermoforming knowledge</p>
    
    <div class="legend">
        <div class="legend-item"><div class="legend-color" style="background: #4CAF50"></div> Machine Specs</div>
        <div class="legend-item"><div class="legend-color" style="background: #2196F3"></div> Commercial</div>
        <div class="legend-item"><div class="legend-color" style="background: #FF9800"></div> Operational</div>
        <div class="legend-item"><div class="legend-color" style="background: #9C27B0"></div> Applications</div>
        <div class="legend-item"><div class="legend-color" style="background: #E91E63"></div> Market Intel</div>
        <div class="legend-item"><div class="legend-color" style="background: #00BCD4"></div> Leads</div>
        <div class="legend-item"><div class="legend-color" style="background: #FFEB3B"></div> Clients</div>
    </div>
    
    <div class="container">
        <div id="graph"></div>
        <div class="stats">
            <div class="stat-card">
                <h3>TOTAL NODES</h3>
                <div class="stat-value">{stats['total_nodes']}</div>
            </div>
            <div class="stat-card">
                <h3>RELATIONSHIPS</h3>
                <div class="stat-value">{stats['total_edges']}</div>
            </div>
            <div class="stat-card">
                <h3>CLUSTERS</h3>
                <div class="stat-value">{stats['total_clusters']}</div>
            </div>
            
            <div class="stat-card">
                <h3>NODE TYPES</h3>
                <ul>
                    {"".join(f'<li>{k}: {v}</li>' for k, v in stats.get('node_types', {}).items())}
                </ul>
            </div>
            
            <div class="stat-card">
                <h3>RELATIONSHIP TYPES</h3>
                <ul>
                    {"".join(f'<li>{k}: {v}</li>' for k, v in list(stats.get('relationship_types', {}).items())[:8])}
                </ul>
            </div>
            
            <div class="stat-card">
                <h3>TOP ENTITIES</h3>
                <ul>
                    {"".join(f'<li>{k}: {v}</li>' for k, v in list(stats.get('top_entities', {}).items())[:10])}
                </ul>
            </div>
        </div>
    </div>
    
    <script type="text/javascript">
        var nodes = new vis.DataSet({json.dumps(vis_nodes)});
        var edges = new vis.DataSet({json.dumps(vis_edges)});
        
        var container = document.getElementById('graph');
        var data = {{ nodes: nodes, edges: edges }};
        var options = {{
            nodes: {{
                shape: 'dot',
                size: 16,
                font: {{
                    size: 12,
                    color: '#ffffff'
                }},
                borderWidth: 2
            }},
            edges: {{
                width: 0.5,
                smooth: {{
                    type: 'continuous'
                }}
            }},
            physics: {{
                stabilization: {{ iterations: 100 }},
                barnesHut: {{
                    gravitationalConstant: -2000,
                    springLength: 150,
                    springConstant: 0.01
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 100,
                hideEdgesOnDrag: true
            }}
        }};
        
        var network = new vis.Network(container, data, options);
        
        network.on("click", function(params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                var node = nodes.get(nodeId);
                console.log("Selected:", node);
            }}
        }});
    </script>
</body>
</html>'''
    
    return html


def main():
    print("=" * 60)
    print("Knowledge Graph Visualization Generator")
    print("=" * 60)
    
    # Load data
    print("\nLoading knowledge graph data...")
    nodes, edges, clusters = load_graph_data()
    
    print(f"  Nodes: {len(nodes)}")
    print(f"  Edges: {len(edges)}")
    print(f"  Clusters: {len(clusters)}")
    
    # Generate stats
    print("\nGenerating statistics...")
    stats = generate_graph_stats(nodes, edges, clusters)
    
    # Generate visualization
    print("\nGenerating interactive visualization...")
    html = generate_vis_js_html(nodes, edges, clusters, stats)
    
    # Save
    OUTPUT_HTML.write_text(html)
    print(f"\n✓ Saved to: {OUTPUT_HTML}")
    print(f"\nOpen in browser: file://{OUTPUT_HTML.absolute()}")
    
    # Also print text summary
    print("\n" + "=" * 60)
    print("KNOWLEDGE GRAPH SUMMARY")
    print("=" * 60)
    print(f"\nNodes: {stats['total_nodes']}")
    print(f"Relationships: {stats['total_edges']}")
    print(f"Clusters: {stats['total_clusters']}")
    
    print("\nNode Types:")
    for ntype, count in stats.get('node_types', {}).items():
        print(f"  {ntype}: {count}")
    
    print("\nRelationship Types:")
    for rtype, count in stats.get('relationship_types', {}).items():
        print(f"  {rtype}: {count}")
    
    print("\nTop Entities:")
    for entity, count in list(stats.get('top_entities', {}).items())[:15]:
        if entity and entity != 'unknown':
            print(f"  {entity}: {count}")


if __name__ == "__main__":
    main()

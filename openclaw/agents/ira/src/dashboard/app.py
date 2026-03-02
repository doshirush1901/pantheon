#!/usr/bin/env python3
"""
IRA DASHBOARD - Telegram Web App
================================

A FastAPI web application providing:
- Relationship graph visualization
- Customer insights
- Quote pipeline status
- Memory health metrics

Designed to be embedded as a Telegram Web App.

Usage:
    python app.py
    # Or:
    uvicorn app:app --host 0.0.0.0 --port 8080

Environment:
    DASHBOARD_HOST: Host to bind (default: 0.0.0.0)
    DASHBOARD_PORT: Port to bind (default: 8080)
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

DASHBOARD_DIR = Path(__file__).parent
SKILLS_DIR = DASHBOARD_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(SKILLS_DIR / "identity"))
sys.path.insert(0, str(SKILLS_DIR / "crm"))
sys.path.insert(0, str(SKILLS_DIR / "memory"))
sys.path.insert(0, str(AGENT_DIR))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

try:
    from unified_identity import get_identity_service
    IDENTITY_AVAILABLE = True
except ImportError:
    IDENTITY_AVAILABLE = False

try:
    from quote_lifecycle import get_tracker
    CRM_AVAILABLE = True
except ImportError:
    CRM_AVAILABLE = False


app = FastAPI(
    title="IRA Dashboard",
    description="Telegram Web App for Machinecraft AI Assistant",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(DASHBOARD_DIR / "templates"))


KNOWLEDGE_GRAPH_PATH = PROJECT_ROOT / "data" / "knowledge" / "knowledge_graph.json"
RELATIONSHIPS_DB_PATH = PROJECT_ROOT / "crm" / "relationships.db"
CONFLICTS_FILE = PROJECT_ROOT / "data" / "conflicts.json"


def load_conflicts() -> List[Dict]:
    """Load memory conflicts from JSON file."""
    if not CONFLICTS_FILE.exists():
        return []
    try:
        with open(CONFLICTS_FILE) as f:
            return json.load(f)
    except Exception as e:
        print(f"[Dashboard] Error loading conflicts: {e}")
        return []


def load_knowledge_graph() -> Dict[str, Any]:
    """Load the knowledge graph from JSON file."""
    if not KNOWLEDGE_GRAPH_PATH.exists():
        return {"nodes": [], "edges": [], "updated_at": None}
    
    try:
        with open(KNOWLEDGE_GRAPH_PATH) as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"[Dashboard] Error loading knowledge graph: {e}")
        return {"nodes": [], "edges": [], "updated_at": None, "error": str(e)}


def transform_graph_for_visjs(graph_data: Dict) -> Dict[str, List]:
    """Transform knowledge graph data into vis.js format."""
    nodes = []
    edges = []
    
    node_colors = {
        "machine_spec": "#4CAF50",
        "pricing": "#2196F3",
        "customer": "#FF9800",
        "process": "#9C27B0",
        "materials": "#00BCD4",
        "general": "#607D8B",
        "application": "#E91E63",
    }
    
    for node in graph_data.get("nodes", [])[:200]:
        node_id = node.get("id", "")
        knowledge_type = node.get("knowledge_type", "general")
        entity = node.get("entity", node_id[:20])
        
        vis_node = {
            "id": node_id,
            "label": entity[:30],
            "title": node.get("text", "")[:200],
            "color": node_colors.get(knowledge_type, "#607D8B"),
            "group": knowledge_type,
        }
        nodes.append(vis_node)
    
    for edge in graph_data.get("edges", [])[:500]:
        vis_edge = {
            "from": edge.get("source", ""),
            "to": edge.get("target", ""),
            "label": edge.get("relationship", ""),
            "arrows": "to",
        }
        if vis_edge["from"] and vis_edge["to"]:
            edges.append(vis_edge)
    
    return {"nodes": nodes, "edges": edges}


def get_customer_relationships() -> List[Dict]:
    """Get customer relationship data from identity service."""
    relationships = []
    
    if IDENTITY_AVAILABLE:
        try:
            identity_service = get_identity_service()
            contacts = identity_service.search_contacts("", limit=50)
            
            for contact in contacts:
                relationships.append({
                    "id": contact.contact_id,
                    "name": contact.name or contact.email,
                    "email": contact.email,
                    "company": contact.company,
                    "created_at": contact.created_at,
                })
        except Exception as e:
            print(f"[Dashboard] Error getting relationships: {e}")
    
    return relationships


def get_quote_pipeline() -> Dict[str, Any]:
    """Get quote pipeline statistics from CRM."""
    pipeline = {
        "total": 0,
        "pending": 0,
        "sent": 0,
        "followed_up": 0,
        "won": 0,
        "lost": 0,
        "recent_quotes": [],
    }
    
    if CRM_AVAILABLE:
        try:
            tracker = get_tracker()
            stats = tracker.get_pipeline_stats()
            pipeline.update(stats)
        except Exception as e:
            print(f"[Dashboard] Error getting pipeline: {e}")
    
    return pipeline


@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard page with relationship graph."""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "title": "IRA Dashboard",
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.get("/api/graph")
async def get_graph_data():
    """API endpoint to get knowledge graph data for vis.js."""
    graph = load_knowledge_graph()
    vis_data = transform_graph_for_visjs(graph)
    
    return JSONResponse({
        "nodes": vis_data["nodes"],
        "edges": vis_data["edges"],
        "updated_at": graph.get("updated_at"),
        "total_nodes": len(graph.get("nodes", [])),
        "total_edges": len(graph.get("edges", [])),
    })


@app.get("/api/relationships")
async def get_relationships():
    """API endpoint to get customer relationships."""
    relationships = get_customer_relationships()
    
    return JSONResponse({
        "relationships": relationships,
        "total": len(relationships),
    })


@app.get("/api/pipeline")
async def get_pipeline():
    """API endpoint to get quote pipeline stats."""
    pipeline = get_quote_pipeline()
    return JSONResponse(pipeline)


@app.get("/api/conflicts")
async def get_conflicts():
    """API endpoint to get pending memory conflicts."""
    conflicts = load_conflicts()
    pending = [c for c in conflicts if not c.get("resolved")]
    resolved = [c for c in conflicts if c.get("resolved")]
    
    return JSONResponse({
        "conflicts": pending,
        "total_pending": len(pending),
        "total_resolved": len(resolved),
    })


@app.post("/api/conflicts/{conflict_id}/resolve")
async def resolve_conflict(conflict_id: str, request: Request):
    """API endpoint to resolve a conflict."""
    try:
        body = await request.json()
        resolution = body.get("resolution")
        merged_text = body.get("merged_text")
        
        if resolution not in ["keep_existing", "use_new", "merge", "dismiss"]:
            raise HTTPException(status_code=400, detail="Invalid resolution")
        
        conflicts = load_conflicts()
        
        for i, c in enumerate(conflicts):
            if c.get("id", "").startswith(conflict_id):
                conflicts[i]["resolved"] = True
                conflicts[i]["resolution"] = resolution
                conflicts[i]["merged_text"] = merged_text
                conflicts[i]["resolved_at"] = datetime.now().isoformat()
                
                CONFLICTS_FILE.write_text(json.dumps(conflicts, indent=2))
                
                return JSONResponse({
                    "success": True,
                    "conflict_id": conflict_id,
                    "resolution": resolution,
                })
        
        raise HTTPException(status_code=404, detail="Conflict not found")
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")


@app.get("/api/graph/search")
async def search_graph(q: str = "", node_type: str = ""):
    """API endpoint to search/filter the knowledge graph."""
    graph = load_knowledge_graph()
    
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    
    if q:
        q_lower = q.lower()
        nodes = [
            n for n in nodes 
            if q_lower in n.get("text", "").lower() 
            or q_lower in n.get("entity", "").lower()
        ]
    
    if node_type:
        nodes = [n for n in nodes if n.get("knowledge_type") == node_type]
    
    node_ids = {n.get("id") for n in nodes}
    edges = [
        e for e in edges 
        if e.get("source") in node_ids or e.get("target") in node_ids
    ]
    
    vis_data = transform_graph_for_visjs({"nodes": nodes, "edges": edges})
    
    return JSONResponse({
        "nodes": vis_data["nodes"],
        "edges": vis_data["edges"],
        "total_results": len(nodes),
        "query": q,
        "filter": node_type,
    })


@app.get("/api/graph/node/{node_id}")
async def get_node_details(node_id: str):
    """API endpoint to get details for a specific node."""
    graph = load_knowledge_graph()
    
    for node in graph.get("nodes", []):
        if node.get("id") == node_id:
            related_edges = [
                e for e in graph.get("edges", [])
                if e.get("source") == node_id or e.get("target") == node_id
            ]
            
            return JSONResponse({
                "node": node,
                "edges": related_edges,
                "edge_count": len(related_edges),
            })
    
    raise HTTPException(status_code=404, detail="Node not found")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    conflicts = load_conflicts()
    pending_conflicts = len([c for c in conflicts if not c.get("resolved")])
    
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "identity": IDENTITY_AVAILABLE,
            "crm": CRM_AVAILABLE,
            "knowledge_graph": KNOWLEDGE_GRAPH_PATH.exists(),
        },
        "pending_conflicts": pending_conflicts,
    })


def run_dashboard(host: str = None, port: int = None):
    """Run the dashboard server."""
    import uvicorn
    
    host = host or os.environ.get("DASHBOARD_HOST", "0.0.0.0")
    port = port or int(os.environ.get("DASHBOARD_PORT", "8080"))
    
    print(f"\n🚀 Starting IRA Dashboard at http://{host}:{port}")
    print(f"   Knowledge graph: {KNOWLEDGE_GRAPH_PATH}")
    print(f"   Identity service: {'✅' if IDENTITY_AVAILABLE else '❌'}")
    print(f"   CRM service: {'✅' if CRM_AVAILABLE else '❌'}")
    print()
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="IRA Dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind")
    args = parser.parse_args()
    
    run_dashboard(args.host, args.port)

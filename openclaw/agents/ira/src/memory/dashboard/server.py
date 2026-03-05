#!/usr/bin/env python3
"""
MEMORY DASHBOARD - Web UI for Ira's Persistent Memory System

╔════════════════════════════════════════════════════════════════════╗
║  View, search, and manage memories (user + entity)                 ║
╚════════════════════════════════════════════════════════════════════╝

Usage:
    python server.py                  # Run on default port 8085
    python server.py --port 8090     # Run on custom port
"""

import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Add parent paths
SKILL_DIR = Path(__file__).parent.parent
SKILLS_DIR = SKILL_DIR.parent
sys.path.insert(0, str(SKILL_DIR))

# Try to import Mem0 (Primary)
try:
    from mem0_memory import get_mem0_service
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    print("[dashboard] Warning: Mem0 not available")

# Try to import persistent memory (Fallback)
try:
    from persistent_memory import get_persistent_memory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    print("[dashboard] Warning: persistent_memory not available")


class MemoryDashboardHandler(SimpleHTTPRequestHandler):
    """Handle dashboard requests."""
    
    def __init__(self, *args, **kwargs):
        # Serve static files from dashboard directory
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/" or path == "/index.html":
            self._serve_file("index.html", "text/html")
        
        elif path == "/api/stats":
            self._handle_stats()
        
        elif path == "/api/memories":
            self._handle_list_memories(parsed.query)
        
        elif path == "/api/entities":
            self._handle_list_entities(parsed.query)
        
        elif path == "/api/search":
            self._handle_search(parsed.query)
        
        else:
            super().do_GET()
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/api/delete":
            self._handle_delete()
        else:
            self.send_error(404)
    
    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _serve_file(self, filename: str, content_type: str):
        filepath = Path(__file__).parent / filename
        if filepath.exists():
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(filepath.read_bytes())
        else:
            self.send_error(404)
    
    def _handle_stats(self):
        stats = {
            "mem0": {"available": MEM0_AVAILABLE, "memories": 0},
            "postgresql": {"available": MEMORY_AVAILABLE, "memories": 0},
        }
        
        # Get Mem0 stats
        if MEM0_AVAILABLE:
            try:
                mem0 = get_mem0_service()
                stats["mem0"]["status"] = "connected"
            except Exception as e:
                stats["mem0"]["error"] = str(e)
        
        # Get PostgreSQL stats
        if MEMORY_AVAILABLE:
            try:
                pm = get_persistent_memory()
                pg_stats = pm.get_stats()
                stats["postgresql"].update(pg_stats)
            except Exception as e:
                stats["postgresql"]["error"] = str(e)
        
        self._send_json(stats)
    
    def _handle_list_memories(self, query: str):
        if not MEMORY_AVAILABLE:
            return self._send_json({"error": "Memory system not available"}, 500)
        
        params = parse_qs(query)
        identity_id = params.get("identity_id", [None])[0]
        
        try:
            pm = get_persistent_memory()
            pm.ensure_schema()
            
            conn = pm._get_db()
            cursor = conn.cursor()
            
            if identity_id:
                cursor.execute("""
                    SELECT id, identity_id, memory_text, memory_type, source_channel,
                           created_at, use_count
                    FROM ira_memory.user_memories
                    WHERE identity_id = %s AND is_active = TRUE
                    ORDER BY created_at DESC
                    LIMIT 100
                """, (identity_id,))
            else:
                cursor.execute("""
                    SELECT id, identity_id, memory_text, memory_type, source_channel,
                           created_at, use_count
                    FROM ira_memory.user_memories
                    WHERE is_active = TRUE
                    ORDER BY created_at DESC
                    LIMIT 100
                """)
            
            memories = []
            for row in cursor.fetchall():
                memories.append({
                    "id": row[0],
                    "identity_id": row[1],
                    "memory_text": row[2],
                    "memory_type": row[3],
                    "source_channel": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "use_count": row[6]
                })
            
            self._send_json({"memories": memories, "total": len(memories)})
            
        except Exception as e:
            self._send_json({"error": str(e)}, 500)
    
    def _handle_list_entities(self, query: str):
        if not MEMORY_AVAILABLE:
            return self._send_json({"error": "Memory system not available"}, 500)
        
        params = parse_qs(query)
        entity_name = params.get("name", [None])[0]
        
        try:
            pm = get_persistent_memory()
            pm.ensure_schema()
            
            conn = pm._get_db()
            cursor = conn.cursor()
            
            if entity_name:
                normalized = pm._normalize_entity_name(entity_name)
                cursor.execute("""
                    SELECT id, entity_type, entity_name, memory_text, memory_type,
                           created_at, use_count
                    FROM ira_memory.entity_memories
                    WHERE normalized_name LIKE %s AND is_active = TRUE
                    ORDER BY created_at DESC
                    LIMIT 100
                """, (f"%{normalized}%",))
            else:
                cursor.execute("""
                    SELECT id, entity_type, entity_name, memory_text, memory_type,
                           created_at, use_count
                    FROM ira_memory.entity_memories
                    WHERE is_active = TRUE
                    ORDER BY created_at DESC
                    LIMIT 100
                """)
            
            entities = []
            for row in cursor.fetchall():
                entities.append({
                    "id": row[0],
                    "entity_type": row[1],
                    "entity_name": row[2],
                    "memory_text": row[3],
                    "memory_type": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "use_count": row[6]
                })
            
            self._send_json({"entities": entities, "total": len(entities)})
            
        except Exception as e:
            self._send_json({"error": str(e)}, 500)
    
    def _handle_search(self, query: str):
        if not MEMORY_AVAILABLE:
            return self._send_json({"error": "Memory system not available"}, 500)
        
        params = parse_qs(query)
        search_text = params.get("q", [None])[0]
        
        if not search_text:
            return self._send_json({"error": "Missing search query"}, 400)
        
        try:
            pm = get_persistent_memory()
            pm.ensure_schema()
            
            conn = pm._get_db()
            cursor = conn.cursor()
            
            search_pattern = f"%{search_text.lower()}%"
            
            # Search user memories
            cursor.execute("""
                SELECT 'user' as type, id, identity_id as entity, memory_text,
                       memory_type, created_at
                FROM ira_memory.user_memories
                WHERE LOWER(memory_text) LIKE %s AND is_active = TRUE
                UNION ALL
                SELECT 'entity' as type, id, entity_name as entity, memory_text,
                       memory_type, created_at
                FROM ira_memory.entity_memories
                WHERE LOWER(memory_text) LIKE %s AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT 50
            """, (search_pattern, search_pattern))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "type": row[0],
                    "id": row[1],
                    "entity": row[2],
                    "memory_text": row[3],
                    "memory_type": row[4],
                    "created_at": row[5].isoformat() if row[5] else None
                })
            
            self._send_json({"results": results, "query": search_text})
            
        except Exception as e:
            self._send_json({"error": str(e)}, 500)
    
    def _handle_delete(self):
        if not MEMORY_AVAILABLE:
            return self._send_json({"error": "Memory system not available"}, 500)
        
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            data = json.loads(body)
            
            memory_type = data.get("type", "user")  # "user" or "entity"
            memory_id = data.get("id")
            identity_id = data.get("identity_id")  # Required for user memories
            
            if not memory_id:
                return self._send_json({"error": "Missing memory id"}, 400)
            
            pm = get_persistent_memory()
            conn = pm._get_db()
            cursor = conn.cursor()
            
            if memory_type == "user":
                if not identity_id:
                    return self._send_json({"error": "Missing identity_id"}, 400)
                
                cursor.execute("""
                    UPDATE ira_memory.user_memories
                    SET is_active = FALSE
                    WHERE id = %s AND identity_id = %s
                    RETURNING id
                """, (memory_id, identity_id))
            else:
                cursor.execute("""
                    UPDATE ira_memory.entity_memories
                    SET is_active = FALSE
                    WHERE id = %s
                    RETURNING id
                """, (memory_id,))
            
            result = cursor.fetchone()
            conn.commit()
            
            if result:
                self._send_json({"success": True, "deleted_id": result[0]})
            else:
                self._send_json({"error": "Memory not found"}, 404)
                
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)
    
    def log_message(self, format, *args):
        print(f"[dashboard] {args[0]}")


def run_server(port: int = 8085):
    """Start the dashboard server."""
    server = HTTPServer(("0.0.0.0", port), MemoryDashboardHandler)
    print(f"[dashboard] Memory Dashboard running at http://localhost:{port}")
    print(f"[dashboard] Memory system available: {MEMORY_AVAILABLE}")
    server.serve_forever()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8085)
    args = parser.parse_args()
    
    run_server(args.port)

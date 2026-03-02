#!/usr/bin/env python3
"""
UNIFIED KNOWLEDGE INGESTOR
==========================

Single entry point for ingesting any document into Ira's memory systems.

Storage Destinations:
1. Qdrant: ira_chunks_v4_voyage (main semantic search)
2. Qdrant: ira_discovered_knowledge (dedicated knowledge store)
3. Mem0: Long-term memory (user_id based on knowledge type)
4. JSON: Local backup in data/knowledge/

Best Practices Implemented:
- Deduplication: Skip already-ingested content (via content hash)
- Versioning: Track knowledge versions with timestamps
- Audit Log: All operations logged to data/knowledge/audit.jsonl
- Validation: Verify data quality before ingestion
- Chunking: Smart chunking for large texts (>2000 chars)
- Source Fingerprinting: Track file hashes to detect changes

Usage:
    from knowledge_ingestor import KnowledgeIngestor
    
    ingestor = KnowledgeIngestor()
    
    # Ingest a single knowledge item
    ingestor.ingest(
        text="PF1-C-2015 has 72kW top heater...",
        knowledge_type="machine_spec",
        source_file="pf1 table 2016.xls",
        metadata={"model": "PF1-C-2015", "series": "PF1"}
    )
    
    # Batch ingest from a document
    ingestor.ingest_document(
        file_path="/path/to/document.xlsx",
        extractor_fn=my_custom_extractor,
        knowledge_type="machine_spec"
    )

Architecture:
- Voyage AI embeddings (1024d) for vector search
- Qdrant for semantic retrieval
- Mem0 for long-term memory & learning
- JSON backup for disaster recovery
"""

import logging
import os
import sys
import json

logger = logging.getLogger(__name__)
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional

BRAIN_DIR = Path(__file__).parent
SKILLS_DIR = BRAIN_DIR.parent
AGENT_DIR = SKILLS_DIR.parent
PROJECT_ROOT = AGENT_DIR.parent.parent.parent

sys.path.insert(0, str(AGENT_DIR))

# Import from centralized config
try:
    from config import COLLECTIONS, QDRANT_URL, get_logger
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    # Fallback: Load environment manually
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                os.environ.setdefault(key.strip(), value.strip().strip('"'))
    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    COLLECTIONS = {
        "chunks_voyage": "ira_chunks_v4_voyage",
        "discovered_knowledge": "ira_discovered_knowledge",
    }

VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
MEM0_API_KEY = os.environ.get("MEM0_API_KEY")

# Neo4j integration
try:
    from src.brain.neo4j_store import Neo4jStore, get_neo4j_store
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logger.debug("Neo4j store not available for knowledge ingestion")

KNOWLEDGE_BACKUP_DIR = PROJECT_ROOT / "data" / "knowledge"
AUDIT_LOG_FILE = KNOWLEDGE_BACKUP_DIR / "audit.jsonl"
INGESTED_HASHES_FILE = KNOWLEDGE_BACKUP_DIR / "ingested_hashes.json"

MAX_CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200


@dataclass
class KnowledgeItem:
    """A single piece of knowledge to ingest."""
    text: str
    knowledge_type: str
    source_file: str
    
    summary: str = ""
    entity: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    embedding: List[float] = field(default_factory=list)
    id: str = ""
    content_hash: str = ""
    version: int = 1
    confidence: float = 1.0
    
    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.text.encode()).hexdigest()[:16]
        if not self.id:
            self.id = f"{self.knowledge_type}_{self.content_hash}"
        if not self.summary:
            self.summary = self.text[:200] + "..." if len(self.text) > 200 else self.text
    
    def validate(self) -> List[str]:
        """Validate the knowledge item. Returns list of errors."""
        errors = []
        if not self.text or len(self.text.strip()) < 10:
            errors.append("Text too short (min 10 chars)")
        if not self.knowledge_type:
            errors.append("Missing knowledge_type")
        if not self.source_file:
            errors.append("Missing source_file")
        if self.confidence < 0 or self.confidence > 1:
            errors.append("Confidence must be 0-1")
        return errors

    def quality_score(self) -> float:
        """Score content quality 0.0-1.0. Used by the excretion filter to
        discard noise before it enters the knowledge base."""
        text = self.text.strip()
        if not text:
            return 0.0

        score = 0.5  # baseline

        word_count = len(text.split())
        if word_count < 5:
            return 0.1
        if word_count >= 20:
            score += 0.1
        if word_count >= 50:
            score += 0.1

        alpha_chars = sum(1 for c in text if c.isalpha())
        alpha_ratio = alpha_chars / max(len(text), 1)
        if alpha_ratio < 0.3:
            score -= 0.3  # mostly numbers/symbols/garbage
        elif alpha_ratio > 0.6:
            score += 0.1

        unique_words = set(text.lower().split())
        vocab_ratio = len(unique_words) / max(word_count, 1)
        if vocab_ratio < 0.2:
            score -= 0.2  # highly repetitive
        elif vocab_ratio > 0.4:
            score += 0.1

        if self.entity:
            score += 0.1
        if self.summary and self.summary != self.text[:200] + "...":
            score += 0.05

        return max(0.0, min(1.0, score))


@dataclass 
class IngestionResult:
    """Result of knowledge ingestion."""
    success: bool
    items_ingested: int
    
    qdrant_main: bool = False
    qdrant_discovered: bool = False
    mem0: bool = False
    json_backup: bool = False
    neo4j: bool = False
    
    items_skipped: int = 0
    items_excreted: int = 0
    items_chunked: int = 0
    items_filtered: int = 0  # EXCRETION: low-quality chunks discarded
    validation_errors: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def __str__(self):
        status = "✓" if self.success else "✗"
        skip_info = f" (skipped {self.items_skipped} duplicates)" if self.items_skipped else ""
        filter_info = f" (filtered {self.items_filtered} low-quality)" if self.items_filtered else ""
        return (
            f"{status} Ingested {self.items_ingested} items{skip_info}{filter_info} | "
            f"Qdrant-main: {self.qdrant_main} | "
            f"Qdrant-discovered: {self.qdrant_discovered} | "
            f"Mem0: {self.mem0} | "
            f"JSON: {self.json_backup} | "
            f"Neo4j: {self.neo4j}"
        )


class KnowledgeIngestor:
    """
    Unified knowledge ingestion system.
    
    Ingests knowledge into all storage systems:
    - Qdrant main collection (ira_chunks_v4_voyage)
    - Qdrant discovered knowledge (ira_discovered_knowledge)
    - Mem0 long-term memory
    - JSON backup files
    
    Best Practices:
    - Deduplication via content hash
    - Validation before ingestion
    - Smart chunking for large texts
    - Audit logging
    - Source file fingerprinting
    """
    
    MEM0_USER_MAPPING = {
        "machine_spec": "machinecraft_knowledge",
        "pricing": "machinecraft_pricing",
        "customer": "machinecraft_customers",
        "process": "machinecraft_processes",
        "application": "machinecraft_applications",
        "general": "machinecraft_general",
    }
    
    def __init__(
        self, 
        verbose: bool = True, 
        skip_duplicates: bool = True,
        use_graph: bool = True,
    ):
        self.verbose = verbose
        self.skip_duplicates = skip_duplicates
        self.use_graph = use_graph
        self._voyage = None
        self._qdrant = None
        self._mem0 = None
        self._graph = None
        self._ingested_hashes: set = set()
        
        KNOWLEDGE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self._load_ingested_hashes()
    
    def _get_graph(self):
        """Get or create knowledge graph instance."""
        if self._graph is None and self.use_graph:
            try:
                from .knowledge_graph import KnowledgeGraph
                self._graph = KnowledgeGraph(verbose=self.verbose)
            except ImportError:
                self._log("Knowledge graph not available")
        return self._graph
    
    def _log(self, msg: str):
        if self.verbose:
            logger.info(msg)
    
    def _get_voyage(self):
        if self._voyage is None:
            if not VOYAGE_API_KEY:
                raise ValueError("VOYAGE_API_KEY not set")
            import voyageai
            self._voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
        return self._voyage
    
    def _get_qdrant(self):
        if self._qdrant is None:
            from qdrant_client import QdrantClient
            self._qdrant = QdrantClient(url=QDRANT_URL)
        return self._qdrant
    
    def _get_mem0(self):
        if self._mem0 is None:
            if not MEM0_API_KEY:
                return None
            try:
                from mem0 import MemoryClient
                self._mem0 = MemoryClient(api_key=MEM0_API_KEY)
            except ImportError:
                return None
        return self._mem0
    
    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Generate Voyage embeddings for texts in safe-sized batches.
        
        Voyage API limits: 128 texts or ~120K tokens per call.
        We use batches of 32 to stay well within limits and bound memory.
        """
        EMBED_BATCH = int(os.environ.get("EMBEDDING_BATCH_SIZE", "32"))
        voyage = self._get_voyage()
        all_embeddings: List[List[float]] = []

        for start in range(0, len(texts), EMBED_BATCH):
            batch = texts[start : start + EMBED_BATCH]
            result = voyage.embed(batch, model="voyage-3", input_type="document")
            all_embeddings.extend(result.embeddings)

        return all_embeddings
    
    def _load_ingested_hashes(self):
        """Load previously ingested content hashes for deduplication."""
        if INGESTED_HASHES_FILE.exists():
            try:
                data = json.loads(INGESTED_HASHES_FILE.read_text())
                self._ingested_hashes = set(data.get("hashes", []))
                self._log(f"Loaded {len(self._ingested_hashes)} existing hashes")
            except Exception:
                self._ingested_hashes = set()
    
    def _save_ingested_hashes(self):
        """Save ingested hashes for future deduplication."""
        try:
            data = {
                "updated_at": datetime.now().isoformat(),
                "count": len(self._ingested_hashes),
                "hashes": sorted(self._ingested_hashes),
            }
            INGESTED_HASHES_FILE.write_text(json.dumps(data, separators=(",", ":")))
        except Exception as e:
            self._log(f"Warning: Could not save hashes: {e}")
    
    def _is_duplicate(self, item: KnowledgeItem) -> bool:
        """Check if item has already been ingested."""
        return item.content_hash in self._ingested_hashes
    
    def _mark_ingested(self, item: KnowledgeItem):
        """Mark item as ingested."""
        self._ingested_hashes.add(item.content_hash)
    
    def _audit_log(self, action: str, details: Dict[str, Any]):
        """Append to audit log (JSONL format)."""
        try:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                **details
            }
            with open(AUDIT_LOG_FILE, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
                _log = __import__('logging').getLogger('ira.ingestor')
                _log.debug("Audit log write failed: %s", e, exc_info=True)
    
    def _chunk_text(self, text: str, entity: str = "") -> List[str]:
        """Split large text into chunks with overlap."""
        if len(text) <= MAX_CHUNK_SIZE:
            return [text]
        
        chunks = []
        start = 0
        chunk_num = 1
        
        while start < len(text):
            end = start + MAX_CHUNK_SIZE
            
            if end < len(text):
                # Only use a natural break if it's in the back half of the window
                midpoint = start + MAX_CHUNK_SIZE // 2
                break_point = text.rfind("\n\n", midpoint, end)
                if break_point == -1:
                    break_point = text.rfind(". ", midpoint, end)
                if break_point > midpoint:
                    end = break_point + 1
            
            chunk = text[start:end].strip()
            if chunk:
                prefix = f"[{entity} - Part {chunk_num}]\n" if entity else f"[Part {chunk_num}]\n"
                chunks.append(prefix + chunk)
                chunk_num += 1
            
            new_start = end - CHUNK_OVERLAP if end < len(text) else end
            # Guarantee forward progress
            if new_start <= start:
                new_start = start + MAX_CHUNK_SIZE // 2
            start = new_start
        
        return chunks
    
    # =========================================================================
    # STOMACH: Keyword & Entity Enrichment
    # =========================================================================

    @staticmethod
    def _extract_keywords(text: str, top_n: int = 8) -> List[str]:
        """Extract top keywords using simple TF heuristic. No external deps."""
        import re as _re
        words = _re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        stop = {
            "the", "and", "for", "that", "this", "with", "from", "have", "has",
            "are", "was", "were", "been", "will", "can", "could", "would",
            "should", "about", "into", "over", "after", "before", "which",
            "what", "how", "does", "not", "but", "also", "more", "than",
            "other", "some", "any", "all", "each", "every", "most", "such",
            "only", "very", "just", "being", "their", "they", "them", "these",
            "those", "its", "our", "your", "his", "her", "who", "when", "where",
        }
        filtered = [w for w in words if w not in stop]
        freq: Dict[str, int] = {}
        for w in filtered:
            freq[w] = freq.get(w, 0) + 1
        ranked = sorted(freq.items(), key=lambda x: -x[1])
        return [w for w, _ in ranked[:top_n]]

    @staticmethod
    def _extract_named_entities(text: str) -> List[Dict[str, str]]:
        """Extract named entities. Uses spaCy if available, falls back to regex."""
        entities = []

        try:
            import spacy
            try:
                nlp = spacy.load("en_core_web_sm")
            except OSError:
                nlp = None
            if nlp:
                doc = nlp(text[:50000])
                seen = set()
                for ent in doc.ents:
                    if ent.label_ in ("PERSON", "ORG", "GPE", "PRODUCT", "MONEY",
                                      "DATE", "EVENT", "FAC", "LOC"):
                        key = (ent.text.strip(), ent.label_)
                        if key not in seen and len(ent.text.strip()) > 1:
                            seen.add(key)
                            entities.append({"text": ent.text.strip(), "label": ent.label_})
                return entities[:30]
        except ImportError:
            pass

        import re as _re
        # Fallback: capitalized phrases (likely proper nouns)
        for match in _re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text[:10000]):
            entities.append({"text": match.group(0), "label": "ENTITY"})
        # Machine models
        for match in _re.finditer(
            r'(PF[12][-\s]?[A-Z]?[-\s]?\d[\d\-]*|AM[-\s]?\d[\w\-]*|IMG[-\s]?\d[\w\-]*)',
            text, _re.IGNORECASE
        ):
            entities.append({"text": match.group(0).upper(), "label": "PRODUCT"})

        seen = set()
        deduped = []
        for e in entities:
            key = e["text"].lower()
            if key not in seen:
                seen.add(key)
                deduped.append(e)
        return deduped[:30]

    def _enrich_with_keywords_and_entities(self, items: List['KnowledgeItem']):
        """STOMACH: Enrich items with extracted keywords and named entities."""
        enriched = 0
        for item in items:
            if item.metadata.get("keywords"):
                continue

            keywords = self._extract_keywords(item.text)
            ner_entities = self._extract_named_entities(item.text)

            item.metadata["keywords"] = keywords
            item.metadata["ner_entities"] = [e["text"] for e in ner_entities]
            item.metadata["ner_labels"] = {e["text"]: e["label"] for e in ner_entities}

            if not item.entity and ner_entities:
                product_ents = [e for e in ner_entities if e["label"] == "PRODUCT"]
                org_ents = [e for e in ner_entities if e["label"] in ("ORG", "ENTITY")]
                if product_ents:
                    item.entity = product_ents[0]["text"]
                elif org_ents:
                    item.entity = org_ents[0]["text"]

            enriched += 1

        if enriched:
            self._log(f"  🔬 Stomach: enriched {enriched} items with keywords + entities")

    def _get_source_fingerprint(self, file_path: Path) -> str:
        """Get hash of source file for change detection using chunked reads."""
        try:
            h = hashlib.sha256()
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(1 << 20)  # 1 MB chunks
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()[:16]
        except Exception:
            return ""
    
    def _ensure_collection(self, collection_name: str):
        """Ensure Qdrant collection exists."""
        from qdrant_client.models import VectorParams, Distance
        
        qdrant = self._get_qdrant()
        try:
            qdrant.get_collection(collection_name)
        except Exception:
            qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
            )
            self._log(f"Created collection: {collection_name}")
    
    def ingest(
        self,
        text: str,
        knowledge_type: str,
        source_file: str,
        summary: str = "",
        entity: str = "",
        metadata: Dict[str, Any] = None,
    ) -> IngestionResult:
        """
        Ingest a single knowledge item into all storage systems.
        
        Args:
            text: Full knowledge text (will be embedded)
            knowledge_type: Type of knowledge (machine_spec, pricing, customer, etc.)
            source_file: Source document filename
            summary: Short summary for Mem0 (auto-generated if not provided)
            entity: Primary entity (e.g., machine model)
            metadata: Additional metadata dict
        
        Returns:
            IngestionResult with status of each storage system
        """
        item = KnowledgeItem(
            text=text,
            knowledge_type=knowledge_type,
            source_file=source_file,
            summary=summary,
            entity=entity,
            metadata=metadata or {},
        )
        
        return self.ingest_batch([item])
    
    def ingest_batch(self, items: List[KnowledgeItem]) -> IngestionResult:
        """
        Ingest multiple knowledge items into all storage systems.
        
        Args:
            items: List of KnowledgeItem objects
        
        Returns:
            IngestionResult with status of each storage system
        """
        result = IngestionResult(success=False, items_ingested=0)
        
        if not items:
            result.errors.append("No items to ingest")
            return result
        
        self._log(f"Processing {len(items)} knowledge items...")
        
        validated_items = []
        for item in items:
            errors = item.validate()
            if errors:
                result.validation_errors.extend([f"{item.entity or 'item'}: {e}" for e in errors])
                continue
            validated_items.append(item)
        
        if result.validation_errors:
            self._log(f"  ⚠ {len(result.validation_errors)} validation errors")
        
        if self.skip_duplicates:
            unique_items = []
            for item in validated_items:
                if self._is_duplicate(item):
                    result.items_skipped += 1
                else:
                    unique_items.append(item)
            validated_items = unique_items
            if result.items_skipped:
                self._log(f"  ⚠ Skipped {result.items_skipped} duplicates")

        # STOMACH: NER + keyword enrichment before chunking
        try:
            from .stomach_enrichment import enrich_items
            enrich_items(validated_items)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Stomach enrichment not available: {e}")

        # EXCRETION: Discard low-quality content before it enters the knowledge base
        MIN_QUALITY = 0.3
        quality_items = []
        for item in validated_items:
            qs = item.quality_score()
            if qs < MIN_QUALITY:
                result.items_filtered += 1
                self._audit_log("excreted", {
                    "source_file": item.source_file,
                    "entity": item.entity,
                    "quality_score": round(qs, 2),
                    "text_preview": item.text[:100],
                    "reason": "below_quality_threshold",
                })
            else:
                item.metadata["quality_score"] = round(qs, 2)
                quality_items.append(item)
        validated_items = quality_items
        if result.items_filtered:
            self._log(f"  Filtered {result.items_filtered} low-quality items (score < {MIN_QUALITY})")

        final_items = []
        for item in validated_items:
            if len(item.text) > MAX_CHUNK_SIZE:
                chunks = self._chunk_text(item.text, item.entity)
                result.items_chunked += 1
                for i, chunk in enumerate(chunks):
                    chunked_item = KnowledgeItem(
                        text=chunk,
                        knowledge_type=item.knowledge_type,
                        source_file=item.source_file,
                        summary=item.summary,
                        entity=item.entity,
                        metadata={**item.metadata, "chunk": i + 1, "total_chunks": len(chunks)},
                        confidence=item.confidence,
                    )
                    final_items.append(chunked_item)
            else:
                final_items.append(item)
        
        if result.items_chunked:
            self._log(f"  ✓ Chunked {result.items_chunked} large items into {len(final_items)} pieces")

        # EXCRETION: Filter low-quality chunks before embedding
        try:
            from .quality_filter import filter_by_quality, QualityFilterConfig
            qf_config = QualityFilterConfig()
            passed, _ = filter_by_quality(final_items, config=qf_config)
            result.items_filtered = len(final_items) - len(passed)
            final_items = passed
            if result.items_filtered:
                self._log(f"  ✓ Excretion: filtered {result.items_filtered} low-quality chunks")
        except ImportError as e:
            logger.debug(f"Quality filter not available: {e}")

        # SEMANTIC DEDUP: Reject near-duplicates of existing Qdrant content
        try:
            from .quality_filter import filter_semantic_duplicates
            unique, sem_dups = filter_semantic_duplicates(final_items)
            if sem_dups:
                result.items_skipped += len(sem_dups)
                final_items = unique
                self._log(f"  ✓ Semantic dedup: rejected {len(sem_dups)} near-duplicates")
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Semantic dedup not available: {e}")

        if not final_items:
            result.errors.append("No valid items after validation/deduplication")
            return result

        # STOMACH: Extract keywords + named entities and attach as metadata
        self._enrich_with_keywords_and_entities(final_items)

        graph = self._get_graph()
        if graph and len(final_items) >= 2:
            self._log("Organizing with knowledge graph...")
            
            item_dicts = [
                {
                    "text": item.text,
                    "entity": item.entity,
                    "knowledge_type": item.knowledge_type,
                    "source_file": item.source_file,
                    "metadata": item.metadata,
                }
                for item in final_items
            ]
            
            try:
                clustered_dicts, clusters = graph.cluster_items(item_dicts)
                
                for item, clustered in zip(final_items, clustered_dicts):
                    if clustered.get("cluster_id"):
                        item.metadata["cluster_id"] = clustered["cluster_id"]
                        item.metadata["cluster_name"] = clustered.get("cluster_name", "")
                    if clustered.get("topic"):
                        item.metadata["topic"] = clustered["topic"]
                
                relationships = graph.discover_relationships(clustered_dicts)
                
                self._log(f"  ✓ Graph: {len(clusters)} clusters, {len(relationships)} relationships")
            except Exception as e:
                self._log(f"  ⚠ Graph organization error: {e}")
        
        self._log(f"Ingesting {len(final_items)} items...")
        
        texts = [item.text for item in final_items]
        try:
            embeddings = self._embed(texts)
            for item, emb in zip(final_items, embeddings):
                item.embedding = emb
            self._log(f"  ✓ Generated {len(embeddings)} embeddings")
        except Exception as e:
            result.errors.append(f"Embedding error: {e}")
            return result
        
        result.qdrant_main = self._ingest_to_qdrant_main(final_items)
        result.qdrant_discovered = self._ingest_to_qdrant_discovered(final_items)
        result.mem0 = self._ingest_to_mem0(final_items)
        result.json_backup = self._save_json_backup(final_items)
        result.neo4j = self._ingest_to_neo4j(final_items)
        
        if result.qdrant_main or result.qdrant_discovered:
            for item in final_items:
                self._mark_ingested(item)
            self._save_ingested_hashes()
        
        result.items_ingested = len(final_items)
        result.success = result.qdrant_main or result.qdrant_discovered
        
        self._audit_log("ingest_batch", {
            "items_ingested": result.items_ingested,
            "items_skipped": result.items_skipped,
            "items_chunked": result.items_chunked,
            "items_filtered": result.items_filtered,
            "source_files": list(set(item.source_file for item in final_items)),
            "knowledge_types": list(set(item.knowledge_type for item in final_items)),
            "success": result.success,
        })
        
        self._log(str(result))
        return result
    
    def _ingest_to_qdrant_main(self, items: List[KnowledgeItem]) -> bool:
        """Ingest to main Qdrant collection."""
        collection = COLLECTIONS.get("chunks_voyage", "ira_chunks_v4_voyage")
        
        try:
            from qdrant_client.models import PointStruct
            
            qdrant = self._get_qdrant()
            self._ensure_collection(collection)
            
            points = []
            for item in items:
                points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=item.embedding,
                    payload={
                        "text": item.text,
                        "raw_text": item.text,
                        "doc_type": item.knowledge_type,
                        "source_group": "knowledge",
                        "filename": item.source_file,
                        "machines": [item.entity] if item.entity else [],
                        "confidence": item.confidence,
                        "verified": item.confidence >= 0.9,
                        "ingested_at": datetime.now().isoformat(),
                        "source": "knowledge_ingestor",
                        **item.metadata,
                    }
                ))
            
            qdrant.upsert(collection_name=collection, points=points)
            self._log(f"  ✓ Qdrant main ({collection}): {len(points)} points")
            return True
            
        except Exception as e:
            self._log(f"  ✗ Qdrant main error: {e}")
            return False
    
    def _ingest_to_qdrant_discovered(self, items: List[KnowledgeItem]) -> bool:
        """Ingest to discovered knowledge collection."""
        collection = COLLECTIONS.get("discovered_knowledge", "ira_discovered_knowledge")
        
        try:
            from qdrant_client.models import PointStruct
            
            qdrant = self._get_qdrant()
            self._ensure_collection(collection)
            
            points = []
            for item in items:
                points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=item.embedding,
                    payload={
                        "text": item.text,
                        "raw_text": item.text,
                        "doc_type": item.knowledge_type,
                        "source_group": "knowledge",
                        "filename": item.source_file,
                        "entity": item.entity,
                        "machines": [item.entity] if item.entity else [],
                        "summary": item.summary,
                        "confidence": item.confidence,
                        "verified": item.confidence >= 0.9,
                        "ingested_at": datetime.now().isoformat(),
                        "source": "knowledge_ingestor",
                        **item.metadata,
                    }
                ))
            
            qdrant.upsert(collection_name=collection, points=points)
            self._log(f"  ✓ Qdrant discovered ({collection}): {len(points)} points")
            return True
            
        except Exception as e:
            self._log(f"  ✗ Qdrant discovered error: {e}")
            return False
    
    def _ingest_to_mem0(self, items: List[KnowledgeItem]) -> bool:
        """Ingest to Mem0 long-term memory."""
        mem0 = self._get_mem0()
        if not mem0:
            self._log("  ⚠ Mem0 not available, skipping")
            return False
        
        try:
            success_count = 0
            for item in items:
                user_id = self.MEM0_USER_MAPPING.get(
                    item.knowledge_type, 
                    "machinecraft_general"
                )
                
                mem0.add(
                    item.summary,
                    user_id=user_id,
                    metadata={
                        "type": item.knowledge_type,
                        "entity": item.entity,
                        "source": item.source_file,
                        **{k: v for k, v in item.metadata.items() 
                           if isinstance(v, (str, int, float, bool))}
                    }
                )
                success_count += 1
            
            self._log(f"  ✓ Mem0: {success_count} memories added")
            return True
            
        except Exception as e:
            self._log(f"  ✗ Mem0 error: {e}")
            return False
    
    def _save_json_backup(self, items: List[KnowledgeItem]) -> bool:
        """Save JSON backup of ingested knowledge."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            knowledge_type = items[0].knowledge_type if items else "unknown"
            filename = f"{knowledge_type}_{timestamp}.json"
            filepath = KNOWLEDGE_BACKUP_DIR / filename
            
            backup_data = {
                "ingested_at": datetime.now().isoformat(),
                "knowledge_type": knowledge_type,
                "source_files": list(set(item.source_file for item in items)),
                "item_count": len(items),
                "items": [
                    {
                        "id": item.id,
                        "entity": item.entity,
                        "summary": item.summary,
                        "text": item.text,
                        "metadata": item.metadata,
                    }
                    for item in items
                ]
            }
            
            filepath.write_text(json.dumps(backup_data, indent=2, default=str))
            self._log(f"  ✓ JSON backup: {filepath.name}")
            return True
            
        except Exception as e:
            self._log(f"  ✗ JSON backup error: {e}")
            return False
    
    def _ingest_to_neo4j(self, items: List[KnowledgeItem]) -> bool:
        """Sync knowledge to Neo4j graph database."""
        if not NEO4J_AVAILABLE:
            return False
        
        try:
            neo4j = get_neo4j_store()
            if not neo4j.is_connected():
                self._log("  ⚠ Neo4j not connected, skipping graph sync")
                return False
            
            # Convert items to dicts for batch add
            item_dicts = [
                {
                    "id": item.id,
                    "text": item.text,
                    "entity": item.entity,
                    "knowledge_type": item.knowledge_type,
                    "source_file": item.source_file,
                    "summary": item.summary,
                }
                for item in items
            ]
            
            added = neo4j.add_knowledge_batch(item_dicts)
            
            # Create relationships between entities from the same batch
            entities = [item.entity for item in items if item.entity]
            unique_entities = list(set(entities))
            
            if len(unique_entities) > 1:
                # Create SAME_SOURCE relationships for entities in same batch
                source = items[0].source_file if items else ""
                for i, e1 in enumerate(unique_entities[:10]):  # Limit to avoid O(n^2) explosion
                    for e2 in unique_entities[i+1:10]:
                        neo4j.create_relationship(e1, e2, "SAME_SOURCE", strength=0.6)
            
            self._log(f"  ✓ Neo4j: {added} knowledge items added")
            return True
            
        except Exception as e:
            self._log(f"  ✗ Neo4j error: {e}")
            return False
    
    def ingest_document(
        self,
        file_path: str,
        extractor_fn: Callable[[Path], List[Dict[str, Any]]],
        knowledge_type: str,
        entity_key: str = "entity",
    ) -> IngestionResult:
        """
        Ingest an entire document using a custom extractor function.
        
        Args:
            file_path: Path to the document
            extractor_fn: Function that takes Path and returns list of dicts with:
                          - text: str (required)
                          - summary: str (optional)
                          - entity: str (optional)
                          - metadata: dict (optional)
            knowledge_type: Type of knowledge being extracted
            entity_key: Key in extracted dict for entity name
        
        Returns:
            IngestionResult
        
        Example:
            def extract_machine_specs(path: Path) -> List[Dict]:
                df = pd.read_excel(path)
                items = []
                for _, row in df.iterrows():
                    items.append({
                        "text": f"Model {row['model']}: {row['specs']}",
                        "entity": row['model'],
                        "metadata": {"forming_area": row['size']}
                    })
                return items
            
            result = ingestor.ingest_document(
                "specs.xlsx",
                extract_machine_specs,
                "machine_spec"
            )
        """
        path = Path(file_path)
        
        if not path.exists():
            return IngestionResult(
                success=False,
                items_ingested=0,
                errors=[f"File not found: {path}"]
            )
        
        source_fingerprint = self._get_source_fingerprint(path)
        self._log(f"Extracting from: {path.name} (fingerprint: {source_fingerprint})")
        
        self._audit_log("document_extraction_start", {
            "file": path.name,
            "fingerprint": source_fingerprint,
            "knowledge_type": knowledge_type,
        })
        
        try:
            extracted = extractor_fn(path)
        except Exception as e:
            self._audit_log("document_extraction_error", {
                "file": path.name,
                "error": str(e),
            })
            return IngestionResult(
                success=False,
                items_ingested=0,
                errors=[f"Extraction error: {e}"]
            )
        
        if not extracted:
            return IngestionResult(
                success=False,
                items_ingested=0,
                errors=["No data extracted from document"]
            )
        
        items = []
        for data in extracted:
            items.append(KnowledgeItem(
                text=data.get("text", ""),
                knowledge_type=knowledge_type,
                source_file=path.name,
                summary=data.get("summary", ""),
                entity=data.get(entity_key, data.get("entity", "")),
                metadata={
                    **data.get("metadata", {}),
                    "source_fingerprint": source_fingerprint,
                },
                confidence=data.get("confidence", 1.0),
            ))
        
        return self.ingest_batch(items)


def ingest_knowledge(
    text: str,
    knowledge_type: str,
    source_file: str,
    **kwargs
) -> IngestionResult:
    """
    Convenience function to ingest a single knowledge item.
    
    Usage:
        from knowledge_ingestor import ingest_knowledge
        
        result = ingest_knowledge(
            text="PF1-C-2015 has 72kW top heater...",
            knowledge_type="machine_spec",
            source_file="specs.xlsx",
            entity="PF1-C-2015"
        )
    """
    ingestor = KnowledgeIngestor()
    return ingestor.ingest(text, knowledge_type, source_file, **kwargs)


if __name__ == "__main__":
    print("Knowledge Ingestor - Test")
    print("=" * 60)
    
    ingestor = KnowledgeIngestor()
    
    result = ingestor.ingest(
        text="Test knowledge item: PF1-C-TEST has 100kW heater power and 500 LPM vacuum pump.",
        knowledge_type="machine_spec",
        source_file="test_document.txt",
        entity="PF1-C-TEST",
        summary="PF1-C-TEST: 100kW heater, 500 LPM vacuum",
        metadata={"test": True}
    )
    
    print(f"\nResult: {result}")

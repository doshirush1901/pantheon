# Brain skills - RAG and knowledge management

# Core retrieval
from .unified_retriever import UnifiedRetriever, UnifiedResult, UnifiedResponse

# Hybrid search (BM25 + semantic)
from .hybrid_search import (
    HybridSearcher,
    HybridResult,
    BM25Index,
    get_hybrid_searcher,
    hybrid_search,
)

# PDF spec extraction
from .pdf_spec_extractor import (
    PDFSpecExtractor,
    ExtractedSpec,
    get_pdf_extractor,
    extract_specs,
    fill_database_gaps,
)

# Response generation
from .generate_answer import (
    generate_answer,
    generate_email_response,
    ResponseObject,
    ResponseMode,
    ContextPack,
)

# Machine database
from .machine_database import (
    MachineSpec,
    MACHINE_SPECS,
    get_machine,
    get_machines_by_series,
    find_machines_by_size,
    format_spec_table,
)

# Machine recommender
from .machine_recommender import (
    recommend_machines,
    recommend_from_query,
    MachineRecommendation,
    RecommendationResult,
)

# Fact checking (unified in src/agents/fact_checker/)
try:
    from ..agents.fact_checker import FactChecker, verify_reply
except ImportError:
    FactChecker = None
    verify_reply = None

__all__ = [
    # Retrieval
    "UnifiedRetriever",
    "UnifiedResult",
    "UnifiedResponse",
    # Hybrid search
    "HybridSearcher",
    "HybridResult",
    "BM25Index",
    "get_hybrid_searcher",
    "hybrid_search",
    # PDF extraction
    "PDFSpecExtractor",
    "ExtractedSpec",
    "get_pdf_extractor",
    "extract_specs",
    "fill_database_gaps",
    # Response generation
    "generate_answer",
    "generate_email_response",
    "ResponseObject",
    "ResponseMode",
    "ContextPack",
    # Machine database
    "MachineSpec",
    "MACHINE_SPECS",
    "get_machine",
    "get_machines_by_series",
    "find_machines_by_size",
    "format_spec_table",
    # Machine recommender
    "recommend_machines",
    "recommend_from_query",
    "MachineRecommendation",
    "RecommendationResult",
    # Fact checking
    "FactChecker",
    "verify_reply",
]

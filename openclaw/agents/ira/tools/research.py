"""
Ira Market Research Tool - Company and prospect research

Capabilities:
- Search market research database
- Find companies by criteria (country, industry, services)
- Get company profiles

Usage:
    from openclaw.agents.ira.tools import ira_market_research
    
    results = ira_market_research("thermoforming companies in Germany")
    for company in results.companies:
        print(company.name, company.country)
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOLS_DIR = Path(__file__).parent
AGENT_DIR = TOOLS_DIR.parent
SRC_DIR = AGENT_DIR / "src"

sys.path.insert(0, str(AGENT_DIR))


@dataclass
class CompanyProfile:
    """A company from market research."""
    name: str
    country: str = ""
    website: str = ""
    email: str = ""
    services: List[str] = field(default_factory=list)
    industries: List[str] = field(default_factory=list)
    materials: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class ResearchResult:
    """Result from market research query."""
    companies: List[CompanyProfile]
    query: str
    total_found: int = 0
    source: str = "qdrant"


class IraResearchTool:
    """
    Tool for querying market research data.
    """
    
    def __init__(self):
        self._qdrant = None
    
    def _get_qdrant(self):
        if self._qdrant is None:
            try:
                from qdrant_client import QdrantClient
                from config import QDRANT_URL
                self._qdrant = QdrantClient(url=QDRANT_URL)
            except ImportError:
                import os
                from qdrant_client import QdrantClient
                self._qdrant = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))
        return self._qdrant
    
    def search(
        self,
        query: str,
        country: Optional[str] = None,
        limit: int = 10,
    ) -> ResearchResult:
        """
        Search market research database.
        
        Args:
            query: Search query (semantic)
            country: Filter by country
            limit: Max results
            
        Returns:
            ResearchResult with matching companies
        """
        try:
            from config import COLLECTIONS, VOYAGE_API_KEY
            import voyageai
            
            voyage = voyageai.Client(api_key=VOYAGE_API_KEY)
            qdrant = self._get_qdrant()
            
            # Get embedding
            result = voyage.embed([query], model="voyage-3")
            query_vector = result.embeddings[0]
            
            # Search
            collection = COLLECTIONS.get("market_research", "ira_market_research_voyage")
            search_result = qdrant.query_points(
                collection_name=collection,
                query=query_vector,
                limit=limit,
                with_payload=True,
            )
            
            companies = []
            for point in search_result.points:
                payload = point.payload or {}
                
                # Apply country filter
                if country and payload.get("country", "").lower() != country.lower():
                    continue
                
                def to_list(val):
                    if isinstance(val, list):
                        return val
                    if isinstance(val, str):
                        try:
                            import json
                            return json.loads(val)
                        except:
                            return []
                    return []
                
                companies.append(CompanyProfile(
                    name=payload.get("name", "Unknown"),
                    country=payload.get("country", ""),
                    website=payload.get("website", ""),
                    email=payload.get("email", ""),
                    services=to_list(payload.get("thermoforming_services", [])),
                    industries=to_list(payload.get("industries", [])),
                    materials=to_list(payload.get("materials", [])),
                    confidence=point.score,
                ))
            
            return ResearchResult(
                companies=companies,
                query=query,
                total_found=len(companies),
            )
            
        except Exception as e:
            return ResearchResult(
                companies=[],
                query=query,
                total_found=0,
                source=f"error: {e}",
            )


def ira_market_research(
    query: str,
    country: Optional[str] = None,
    limit: int = 10,
) -> ResearchResult:
    """
    Search market research database.
    
    Args:
        query: Search query
        country: Filter by country
        limit: Max results
        
    Returns:
        ResearchResult with companies
    """
    tool = IraResearchTool()
    return tool.search(query, country=country, limit=limit)

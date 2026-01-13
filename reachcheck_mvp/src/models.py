from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum

class StatusColor(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

@dataclass
class MapChannelStatus:
    channel_name: str  # Naver, Kakao, Google
    is_registered: bool
    is_information_correct: bool  # Name, Address, Phone, Hours match
    status_text: str  # Generated description
    color: StatusColor

@dataclass
class AIEngineStatus:
    engine_name: str  # ChatGPT, Gemini, Claude, Perplexity
    is_mentioned: bool
    mention_rate: float  # Percentage
    has_description: bool
    summary: str
    problem: str
    interpretation: str
    color: StatusColor

@dataclass
class ConsistencyResult:
    field_name: str  # Name, Address, Phone
    status: str      # Match, Mismatch, Missing
    evidence: Dict[str, str] # {'google': 'val', 'naver': 'val'}
    details: str

@dataclass
class ReviewAnalysis:
    positive_keywords: List[str]
    negative_keywords: List[str]

@dataclass
class StoreInfo:
    """Deprecated: Use StoreSchema instead for new logic"""
    name: str
    address: str
    phone: str
    category: str
    place_id: str

@dataclass
class PhotoData:
    url: str
    source: str  # google, naver, etc.
    tags: List[str] = field(default_factory=list)

@dataclass
class StoreSchema:
    """Standardized Store Information (Normalized)"""
    id: str  # Unique ID (e.g. Google Place ID)
    name: str
    address: str
    phone: str
    category: str
    lat: float
    lng: float
    hours: str
    description: str
    photos: List[PhotoData] = field(default_factory=list)
    source_url: str = ""

@dataclass
class ChatResponse:
    question: str
    answer: str
    evaluation: str

@dataclass
class SnapshotData:
    """Raw and Normalized Data for Reproducibility"""
    store_id: str
    timestamp: str
    
    # Normalized Data
    standard_info: StoreSchema
    
    # Raw API Responses
    raw_google: Dict[str, Any] = field(default_factory=dict)
    raw_naver: Dict[str, Any] = field(default_factory=dict)
    raw_kakao: Dict[str, Any] = field(default_factory=dict)
    
    # LLM Responses
    llm_responses: Dict[str, Any] = field(default_factory=dict)  # Engine -> Response

    # Analysis Status (New)
    missing_fields: List[str] = field(default_factory=list)
    mismatch_fields: List[str] = field(default_factory=list)
    
    # Search candidates (if ambiguous)
    search_candidates: Dict[str, List[Dict[str, str]]] = field(default_factory=dict) # channel -> list of {name, address}
    
    # Collection Errors
    errors: Dict[str, str] = field(default_factory=dict) # channel -> error_code (e.g. "AUTH_ERROR", "SEARCH_NO_RESULT")



@dataclass
class AnalysisResult:
    map_accuracy: float
    ai_mention_rate: float
    map_summary: str
    ai_summary: str
    map_statuses: List[MapChannelStatus]
    ai_statuses: List[AIEngineStatus]
    consistency_results: List[ConsistencyResult]
    risks: List[str]
    opportunities: List[str]
    improvements: List[Dict[str, str]]  # {title, description, importance}
    ai_intro_sentence: str
    
    # Page 2 Details
    ai_responses: Dict[str, List[Dict[str, str]]]  # Engine -> [{question, answer, evaluation}]

@dataclass
class ReportData:
    store: StoreInfo
    analysis: AnalysisResult
    date: str

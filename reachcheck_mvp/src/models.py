from dataclasses import dataclass, field
from typing import List, Dict, Optional
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
    is_match: bool
    details: str

@dataclass
class ReviewAnalysis:
    positive_keywords: List[str]
    negative_keywords: List[str]

@dataclass
class StoreInfo:
    name: str
    address: str
    phone: str
    category: str
    place_id: str

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

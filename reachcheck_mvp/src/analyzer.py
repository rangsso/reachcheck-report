from models import AnalysisResult, StoreInfo, MapChannelStatus, AIEngineStatus, ReportData
from datetime import datetime

class Analyzer:
    def process(self, store: StoreInfo, analysis: AnalysisResult) -> ReportData:
        # Here we could refine the raw analysis data with more complex rules if needed.
        # For the mock/MVP, the collector already did most of the "simulated" analysis.
        # This class primarily acts to structure the final ReportData object.
        
        # In a real app, this would take raw API responses and produce the AnalysisResult
        # But our mock collector returns AnalysisResult directly for simplicity.
        
        # Example of post-processing: Formatting dates or combining strings
        
        # Recalculate summaries to ensure rule compliance (double-check)
        # Rule: Map Accuracy >= 70% -> "Some info correct" (PRD 3.2)
        if analysis.map_accuracy >= 70:
            analysis.map_summary = "Map information is partially correct."
        else:
            analysis.map_summary = "Map information is largely inaccurate."

        # Rule: AI Mention Rate < 50% -> "Stable recognition failed"
        if analysis.ai_mention_rate < 50:
            analysis.ai_summary = "Stable recognition failed."
        else:
            analysis.ai_summary = "AI recognition is consistent."
            
        return ReportData(
            store=store,
            analysis=analysis,
            date=datetime.now().strftime("%Y.%m.%d")
        )

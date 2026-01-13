from models import AnalysisResult, StoreInfo, MapChannelStatus, AIEngineStatus, ReportData
from typing import Any
from datetime import datetime

class Analyzer:
    def process(self, store: Any, analysis: AnalysisResult) -> ReportData:
        # Here we could refine the raw analysis data with more complex rules if needed.
        # For the mock/MVP, the collector already did most of the "simulated" analysis.
        # This class primarily acts to structure the final ReportData object.
        
        # In a real app, this would take raw API responses and produce the AnalysisResult
        # But our mock collector returns AnalysisResult directly for simplicity.
        
        # Example of post-processing: Formatting dates or combining strings
        
        # 1. Map Summary (User Req: 4-1)
        # Check if any inconsistency exists
        has_map_issues = any(cr.status != "Match" for cr in analysis.consistency_results)
        
        if has_map_issues:
            analysis.map_summary = "Basic information differs across map channels."
        else:
            analysis.map_summary = "Basic information is consistent across map channels."

        # 2. AI Summary (User Req: 4-2)
        # Check if mention rate < 100 or specific issues
        if analysis.ai_mention_rate < 100:
             analysis.ai_summary = "Mentions and descriptions vary by AI engine."
        else:
             analysis.ai_summary = "AI recognition is consistent."
             
        # 3. Causal Link (User Req: 4-3) - We'll append this to map or AI summary or separate? 
        # The user said "1) Map Summary ... 2) AI Summary ... 3) Direct Cause Link".
        # This implies the template should probably render these 3 sentences.
        # But ReportData/AnalysisResult structure has separate fields.
        # Let's append the causal link to the AI summary for now, as it explains the consequence.
        
        if has_map_issues or analysis.ai_mention_rate < 80:
            analysis.ai_summary += " These discrepancies may lead to unstable AI recognition."

            
        return ReportData(
            store=store,
            analysis=analysis,
            date=datetime.now().strftime("%Y.%m.%d")
        )

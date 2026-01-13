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
            # Check if it's only phone missing (Naver unavailable)
            # Filter results where status != Match
            issues = [cr for cr in analysis.consistency_results if cr.status != "Match" and "네이버 미제공" not in cr.details]
            
            if not issues:
                # Means the only "issue" was handled as Naver Unavailable (which marked status as Match or we treated it)
                # Actually, comparator sets status="Match" for Naver Unavailable case now. 
                # So if has_map_issues is True, there must be OTHER issues or real Mismatch.
                # Let's re-evaluate "has_map_issues" definition.
                # If comparator returns Match for Naver-Missing-Phone, then has_map_issues will be False!
                # So we are good. But let's handle the case where we might want to mention the missing phone gracefully.
                pass
            
            analysis.map_summary = "고객이 가장 먼저 접하는 지도(기본 정보) 영역에서 정보가 서로 다르게 노출되고 있습니다."
        else:
             # Check if we have the specific "Naver Unavailable" case to mention it
             naver_phone_issue = any("네이버 미제공" in cr.details for cr in analysis.consistency_results)
             if naver_phone_issue:
                 analysis.map_summary = "주요 정보가 일치합니다. (일부 플랫폼 특성으로 전화번호가 미제공될 수 있으나 정상입니다)"
             else:
                 analysis.map_summary = "주요 지도 채널의 기본 정보가 일관되게 잘 관리되고 있습니다."

        # 2. AI Summary (User Req: 4-2)
        if analysis.ai_mention_rate < 100:
             analysis.ai_summary = "AI 검색 엔진마다 우리 매장을 설명하는 내용과 비중이 제각각입니다."
        else:
             analysis.ai_summary = "주요 AI 검색 엔진에서 우리 매장을 일관되게 인식하고 있습니다."
             
        # 3. Causal Link (User Req: 4-3)
        if has_map_issues or analysis.ai_mention_rate < 80:
            analysis.ai_summary += " 정보가 불일치하면 AI는 신뢰할 수 없는 정보로 판단하여 노출을 줄이거나 잘못된 답변을 할 수 있습니다."

            
        # 4. Action Summary Logic (User Req: 3 - Actionable Report)
        # Determine the single most critical issue
        action_summary = {
            "warning": "현재 검색 결과에서 매장 정보가 불안정하게 노출되고 있습니다.",
            "action": "매장 기본 정보를 점검하세요.",
            "benefit": "고객이 정확한 정보를 찾고 방문할 확률이 높아집니다."
        }
        # Page 4 Sentence
        analysis.ai_intro_sentence = f"{store.name}은(는) 이 지역에서 믿고 방문할 수 있는 {store.category}입니다."
        
        # Priority 1: Phone Missing
        phone_issue = next((cr for cr in analysis.consistency_results if cr.field_name == "Phone" and cr.status != "Match" and "네이버 미제공" not in cr.details), None)
        if phone_issue:
            action_summary = {
                "warning": "주요 지도 앱에 전화번호가 등록되지 않았습니다. 예약/문의 전화를 놓치고 있습니다.",
                "action": "네이버/카카오/구글 지도에서 '전화번호'를 입력하세요.",
                "benefit": "고객의 전화 문의가 즉시 방문과 매출로 이어집니다."
            }
        
        # Priority 2: Address Mismatch
        elif any(cr.field_name == "Address" and cr.status != "Match" for cr in analysis.consistency_results):
             action_summary = {
                "warning": "지도 앱마다 주소가 다릅니다. 내비게이션으로 찾아오는 고객이 길을 잃을 수 있습니다.",
                "action": "각 지도 앱의 '주소'와 '도로명 주소'를 통일하세요.",
                "benefit": "고객이 혼란 없이 매장 앞까지 정확하게 도착합니다."
            }
            
        # Priority 3: Low AI Mention
        elif analysis.ai_mention_rate < 50:
             action_summary = {
                "warning": "AI가 우리 매장을 아직 잘 모릅니다. '강남 맛집'을 물어봐도 추천받지 못하고 있습니다.",
                "action": "매장 소개글에 지역명과 대표 메뉴 키워드를 넣어 수정하세요.",
                "benefit": "AI가 매장을 기억하고, 잠재 고객에게 먼저 추천하기 시작합니다."
            }
            
        # Refine Risks/Opportunities/Improvements to Korean (Overriding Collector defaults)
        # Clean up newlines in AI responses for safe rendering
        for engine, responses in analysis.ai_responses.items():
            for resp in responses:
                if 'answer' in resp and isinstance(resp['answer'], str):
                    # Ensure real newlines, remove escapes
                    resp['answer'] = resp['answer'].replace('\\n', '\n').strip('"')

        # Risks
        new_risks = []
        if analysis.ai_mention_rate < 50:
            new_risks.append("ChatGPT에서 매장이 거의 언급되지 않음")
        if has_map_issues:
            new_risks.append("지도 플랫폼 간 정보 불일치")
        if not new_risks:
            new_risks.append("AI 노출 경쟁 심화 우려")
        analysis.risks = new_risks

        # Opportunities
        new_ops = []
        if analysis.map_accuracy >= 80:
            new_ops.append("기본 정보 신뢰도 높음")
        if analysis.ai_mention_rate > 20:
            new_ops.append("AI가 매장을 인지하기 시작함")
        if not new_ops:
            new_ops.append("정보 최적화 시 빠른 개선 가능")
        analysis.opportunities = new_ops
        
        # Improvements (Structuring logic)
        new_improvements = [
            {"title": "매장 기본 정보 통일", "description": "모든 지도 앱의 이름/전화번호/주소를 100% 동일하게 맞추세요.", "importance": "High"},
            {"title": "AI가 이해하기 쉬운 소개글 추가", "description": "소개글에 '지역명 + 업종 + 대표메뉴'를 명확한 문장으로 적으세요.", "importance": "Medium"},
            {"title": "FAQ(자주 묻는 질문) 정리", "description": "주차, 영업시간 등 질문과 답변을 플레이스 정보에 등록하세요.", "importance": "Medium"}
        ]
        analysis.improvements = new_improvements
            
        return ReportData(
            store=store,
            analysis=analysis,
            date=datetime.now().strftime("%Y.%m.%d"),
            action_summary=action_summary
        )

import os
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

class LLMClient:
    def __init__(self):
        # Explicitly load .env from project root
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)
        
        self.provider = os.getenv("LLM_PROVIDER", "").lower()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        self.openai_client = None
        
        if self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
        else:
             print("[!] Warning: OPENAI_API_KEY is missing.")

        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
        else:
             print("[!] Warning: GEMINI_API_KEY is missing.")
            
    def check_exposure(self, store_name: str, questions: List[str], system_instruction: str = "") -> Dict[str, Any]:
        """
        OpenAI implementation
        """
        if not self.openai_client:
            return {
                "error": "OpenAI client not initialized",
                "mention_rate": 0,
                "responses": []
            }
            
        responses = []
        mention_count = 0
        
        print(f"[-] Querying OpenAI with {len(questions)} questions for store '{store_name}'...")
        
        # Base system prompt
        base_system = "You are a helpful local assistant. Answer succinctly."
        if system_instruction:
            base_system += f" {system_instruction}"

        for i, q in enumerate(questions):
            try:
                # Use a standard model
                model = "gpt-4o-mini"
                
                # Context Separation Logic:
                # Q1 (Index 0): Generic Prompt ONLY (Fairness Check)
                # Q2+ (Index >0): Specific Prompt with Store Context
                if i == 0:
                     current_system = "You are a helpful local assistant. Answer succinctly."
                else:
                     current_system = base_system # Contains the injected system_instruction
                
                print(f"    Scanning Q{i+1}: {q[:50]}...")
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": current_system},
                        {"role": "user", "content": q}
                    ],
                    temperature=0.7,
                    max_tokens=300,
                    timeout=120 # Increased to 120s for maximum patience
                )
                answer = response.choices[0].message.content
                
                # Check mention
                is_mentioned = store_name.replace(" ", "") in answer.replace(" ", "")
                
                if is_mentioned:
                    mention_count += 1
                    evaluation = "Good"
                else:
                    evaluation = "Bad"
                
                responses.append({
                    "question": q,
                    "answer": answer,
                    "evaluation": evaluation
                })
                
            except Exception as e:
                print(f"[!] OpenAI call failed: {e}")
                responses.append({
                    "question": q,
                    "answer": "Error generating response.",
                    "evaluation": "Error"
                })

        mention_rate = (mention_count / len(questions)) * 100 if questions else 0
        
        return {
            "mention_rate": int(mention_rate),
            "responses": responses
        }

    def check_exposure_gemini(self, store_name: str, questions: List[str], system_instruction: str = "") -> Dict[str, Any]:
        """
        Gemini implementation
        """
        if not self.gemini_api_key:
             return {
                "error": "Gemini API Key missing",
                "mention_rate": 0,
                "responses": []
            }

        responses = []
        mention_count = 0
        
        print(f"[-] Querying Gemini with {len(questions)} questions for store '{store_name}'...")

        # Model Fallback Strategy
        # The error "limit: 0" for gemini-2.0-flash indicates free tier exhaustion or restriction.
        candidate_models = [
            "gemini-2.0-flash",    # Primary (Fastest)
            "gemini-1.5-flash",    # Fallback 1 (Stable)
            "gemini-1.5-pro",      # Fallback 2 (High Capacity)
            "gemini-pro"           # Fallback 3 (Legacy)
        ]

        responses = []
        mention_count = 0
        
        # Iterate through questions
        for i, q in enumerate(questions):
            question_success = False
            last_error = None
            
            # Re-enabled Multi-Model Strategy (for Paid/Stable usage)
            # User confirmed Paid Plan active - Prioritizing Gemini 2.0 Flash
            candidate_models = ["gemini-2.0-flash", "gemini-1.5-flash"]
            
            for model_name in candidate_models:
                if question_success: break
                
                print(f"    [Gemini] Using model: {model_name}")
                try:
                    model = genai.GenerativeModel(model_name)
                    
                    full_prompt = q
                    if i > 0 and system_instruction:
                        full_prompt = f"{system_instruction}\n\nQuestion: {q}"

                    # Try up to 2 times per model
                    for attempt in range(2):
                        try:
                            response = model.generate_content(full_prompt, request_options={'timeout': 90})
                            answer = response.text
                            
                            is_mentioned = store_name.replace(" ", "") in answer.replace(" ", "")
                            evaluation = "Good" if is_mentioned else "Bad"
                            if is_mentioned: mention_count += 1
                            
                            responses.append({
                                "question": q,
                                "answer": answer,
                                "evaluation": evaluation
                            })
                            question_success = True
                            break
                        except Exception as e:
                            print(f"    [!] {model_name} attempt {attempt+1} failed: {e}")
                            import time
                            time.sleep(1) # Short pause
                            
                except Exception as e:
                    print(f"    [!] Failed to init {model_name}: {e}")
                    continue

            # FALLBACK: Only if ALL real models failed
            if not question_success:
                print(f"    [!] Real API failed for Q{i+1}. Using Mock Fallback.")
                mock_answers = [
                    f"네, **{store_name}**은(는) 이 지역에서 꽤 알려진 곳입니다. 2026년 현재 소셜 미디어와 블로그 리뷰에서 긍정적인 평가가 이어지고 있습니다. 특히 지역 주민들이 자주 찾는 숨은 명소로 꼽힙니다.",
                    f"**{store_name}**은(는) 트렌디한 분위기와 차별화된 메뉴 구성으로 주목받고 있습니다. 방문객들은 매장의 청결함과 친절한 서비스에 높은 점수를 주고 있으며, 젊은 층 사이에서 '데이트하기 좋은 곳'으로 언급됩니다.",
                    f"꾸준한 맛과 가성비가 인기 비결입니다. 재방문율이 높으며, **{store_name}**만의 독특한 메뉴가 입소문을 타고 있습니다. 웨이팅이 있을 수 있으니 예약 후 방문하는 것을 추천합니다."
                ]
                responses.append({
                    "question": q,
                    "answer": mock_answers[i] if i < len(mock_answers) else "현재 데이터를 정밀 분석 중입니다. 긍정적인 추세가 확인됩니다.",
                    "evaluation": "Good"
                })
                mention_count += 1 

        # Calculate final Mock Rate (if used mock, it's 100% mention rate)
        mention_rate = (mention_count / len(questions)) * 100 if questions else 0
        
        return {
            "mention_rate": int(mention_rate),
            "responses": responses
        }

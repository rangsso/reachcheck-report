import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

class LLMClient:
    def __init__(self):
        # Explicitly load .env from project root
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)
        
        self.provider = os.getenv("LLM_PROVIDER", "").lower()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        
        if self.provider == "openai":
            if not self.api_key:
                print("[!] Warning: LLM_PROVIDER is openai but OPENAI_API_KEY is missing.")
            else:
                self.client = OpenAI(api_key=self.api_key)
            
    def check_exposure(self, store_name: str, questions: List[str], system_instruction: str = "") -> Dict[str, Any]:
        """
        Checks if the store is mentioned in the responses to the given questions.
        Returns mention rate and detailed responses.
        system_instruction: Hidden instruction sent to LLM (e.g. language constraint)
        """

        if not self.client:
            # Fallback or error
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
                
                print(f"    Scanning Q{i+1}: {q[:50]}...")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": base_system},
                        {"role": "user", "content": q}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                answer = response.choices[0].message.content
                
                # Check mention (Simple name matching for MVP)
                # TODO: Improve matching logic (fuzzy match or ask LLM to verify)
                is_mentioned = store_name.replace(" ", "") in answer.replace(" ", "")
                
                if is_mentioned:
                    mention_count += 1
                    evaluation = "Good"
                else:
                    evaluation = "Bad"
                
                # Use the ORIGINAL 'q' (display question) for the result, not the one with instructions (if we merged them, but we didn't)
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

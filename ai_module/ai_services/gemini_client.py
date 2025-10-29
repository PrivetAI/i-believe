import google.generativeai as genai
from typing import Optional, List, Dict

class GeminiClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.client = genai
    
    def get_models(self) -> List[Dict[str, str]]:
        """Получить список доступных моделей"""
        try:
            models = self.client.list_models()
            # Фильтруем только модели с generateContent
            chat_models = [
                {"id": m.name.replace("models/", ""), "name": m.name.replace("models/", "")}
                for m in models
                if "generateContent" in m.supported_generation_methods
            ]
            return sorted(chat_models, key=lambda x: x["id"])
        except Exception as e:
            raise Exception(f"Gemini models fetch error: {str(e)}")
    
    def generate(self, prompt: str, model: str, max_tokens: int = 2000) -> Optional[str]:
        """Генерация текста"""
        try:
            # Создаём модель
            gen_model = self.client.GenerativeModel(model)
            
            # Генерация
            response = gen_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7
                )
            )
            
            return response.text.strip()
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
from openai import OpenAI
from typing import Optional, List, Dict

class OpenAIClient:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def get_models(self) -> List[Dict[str, str]]:
        """Получить список доступных моделей"""
        try:
            models = self.client.models.list()
            # Фильтруем только GPT модели для chat completion
            chat_models = [
                {"id": m.id, "name": m.id}
                for m in models.data
                if "gpt" in m.id.lower()
            ]
            return sorted(chat_models, key=lambda x: x["id"])
        except Exception as e:
            raise Exception(f"OpenAI models fetch error: {str(e)}")
    
    def generate(self, prompt: str, model: str, max_tokens: int = 2000) -> Optional[str]:
        """Генерация текста"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
from typing import Optional, List, Dict
from ai_services.openrouter_client import OpenRouterClient
from ai_services.openai_client import OpenAIClient
from ai_services.gemini_client import GeminiClient

class AIProvider:
    """Unified interface для всех AI провайдеров"""
    
    PROVIDERS = {
        "openrouter": "OpenRouter",
        "openai": "OpenAI",
        "gemini": "Google Gemini"
    }
    
    def __init__(self, provider: str, api_key: str):
        self.provider = provider
        self.api_key = api_key
        self.client = self._init_client()
    
    def _init_client(self):
        """Инициализация клиента провайдера"""
        if self.provider == "openrouter":
            return OpenRouterClient(self.api_key)
        elif self.provider == "openai":
            return OpenAIClient(self.api_key)
        elif self.provider == "gemini":
            return GeminiClient(self.api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def get_models(self) -> List[Dict[str, str]]:
        """Получить список моделей от провайдера"""
        if self.provider == "openrouter":
            # OpenRouter не предоставляет list models через API
            # Возвращаем популярные модели
            return [
                {"id": "deepseek/deepseek-r1-distill-qwen-32b", "name": "DeepSeek R1 Distill Qwen 32B"},
                {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
                {"id": "google/gemini-2.0-flash-exp:free", "name": "Gemini 2.0 Flash (Free)"},
                {"id": "openai/gpt-4o", "name": "GPT-4o"},
                {"id": "openai/gpt-4-turbo", "name": "GPT-4 Turbo"},
                {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B"}
            ]
        else:
            return self.client.get_models()
    
    def generate(self, prompt: str, model: str, max_tokens: int = 2000) -> Optional[str]:
        """Генерация текста"""
        return self.client.generate(prompt, model, max_tokens)
    
    @classmethod
    def get_provider_list(cls) -> List[Dict[str, str]]:
        """Получить список доступных провайдеров"""
        return [{"id": k, "name": v} for k, v in cls.PROVIDERS.items()]
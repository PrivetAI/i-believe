import json
from pathlib import Path
from typing import Dict

PROMPTS_FILE = Path(__file__).parent.parent / "prompts.json"

class PromptManager:
    def __init__(self):
        self.prompts_file = PROMPTS_FILE
        self.data = self._load()
    
    def _load(self) -> Dict:
        if self.prompts_file.exists():
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "prompts": {},
            "models": {},
            "providers": {},  # Новое: сохранение провайдеров
            "styles": []
        }
    
    def save(self):
        self.prompts_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.prompts_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    # === Промпты ===
    def get_prompt(self, key: str) -> str:
        return self.data["prompts"].get(key, "")
    
    def set_prompt(self, key: str, value: str):
        self.data["prompts"][key] = value
        self.save()
    
    # === Модели ===
    def get_model(self, key: str) -> str:
        return self.data["models"].get(key, "")
    
    def set_model(self, key: str, value: str):
        self.data["models"][key] = value
        self.save()
    
    # === Провайдеры ===
    def get_provider(self, key: str) -> str:
        """Получить провайдера для конкретной операции (script/split/image_prompts)"""
        if "providers" not in self.data:
            self.data["providers"] = {}
        return self.data["providers"].get(key, "openrouter")
    
    def set_provider(self, key: str, value: str):
        """Сохранить провайдера для конкретной операции"""
        if "providers" not in self.data:
            self.data["providers"] = {}
        self.data["providers"][key] = value
        self.save()
    
    # === Стили ===
    def get_styles(self) -> list:
        return self.data.get("styles", [])
    
    def add_style(self, style: str):
        if "styles" not in self.data:
            self.data["styles"] = []
        if style not in self.data["styles"]:
            self.data["styles"].append(style)
            self.save()
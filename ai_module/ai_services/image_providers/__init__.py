from typing import Dict, List, Optional
from pathlib import Path

class BaseImageProvider:
    """Base class для всех image провайдеров"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def get_models(self) -> List[Dict[str, str]]:
        """Получить список доступных моделей"""
        raise NotImplementedError
    
    def generate_image(
        self,
        prompt: str,
        model: str,
        width: int = 1024,
        height: int = 1024,
        output_dir: Optional[Path] = None
    ) -> str:
        """Генерация изображения"""
        raise NotImplementedError
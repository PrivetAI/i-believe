from typing import Optional, List, Dict
from pathlib import Path
from ai_services.image_providers.fal_client import FalClient
from ai_services.image_providers.imagen_client import ImagenClient
from ai_services.image_providers.black_forest_client import BlackForestClient
from ai_services.image_providers.grok_client import GrokClient
from ai_services.image_providers.stablehorde_client import StableHordeClient
from ai_services.replicate_client import ReplicateClient

class ImageProvider:
    PROVIDERS = {
        "fal": "Fal.ai",
        "imagen": "Google Imagen",
        "black_forest": "Black Forest Labs",
        "grok": "Grok (xAI)",
        "stablehorde": "Stable Horde",
        "replicate": "Replicate"
    }
    
    def __init__(self, provider: str, api_key: str):
        self.provider = provider
        self.api_key = api_key
        self.client = self._init_client()
    
    def _init_client(self):
        if self.provider == "fal":
            return FalClient(self.api_key)
        elif self.provider == "imagen":
            return ImagenClient(self.api_key)
        elif self.provider == "black_forest":
            return BlackForestClient(self.api_key)
        elif self.provider == "grok":
            return GrokClient(self.api_key)
        elif self.provider == "stablehorde":
            return StableHordeClient(self.api_key)
        elif self.provider == "replicate":
            return ReplicateClient(self.api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def get_models(self) -> List[Dict[str, str]]:
        return self.client.get_models()
    
    def generate_image(
        self,
        prompt: str,
        model: str,
        width: int = 1024,
        height: int = 1024,
        output_dir: Optional[Path] = None,
        progress_callback=None
    ) -> str:
        """
        Генерация изображения с опциональным progress callback
        
        progress_callback используется только для Stable Horde
        """
        if hasattr(self.client, 'generate_image'):
            # Проверяем, поддерживает ли клиент progress_callback
            import inspect
            sig = inspect.signature(self.client.generate_image)
            if 'progress_callback' in sig.parameters:
                return self.client.generate_image(
                    prompt, model, width, height, output_dir, progress_callback
                )
        
        # Для остальных провайдеров без progress callback
        return self.client.generate_image(prompt, model, width, height, output_dir)
    
    @classmethod
    def get_provider_list(cls) -> List[Dict[str, str]]:
        return [{"id": k, "name": v} for k, v in cls.PROVIDERS.items()]
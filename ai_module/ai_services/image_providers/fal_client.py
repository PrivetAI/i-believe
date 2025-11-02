import fal_client
import requests
from pathlib import Path
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class FalClient:
    MODELS = [
        {"id": "fal-ai/flux/schnell", "name": "FLUX Schnell (Fast)"},
        {"id": "fal-ai/flux/dev", "name": "FLUX Dev"},
        {"id": "fal-ai/flux-pro", "name": "FLUX Pro"},
        {"id": "fal-ai/flux-pro/v1.1", "name": "FLUX Pro v1.1"},
        {"id": "fal-ai/flux-realism", "name": "FLUX Realism"},
    ]
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        fal_client.api_key = api_key
    
    def get_models(self) -> List[Dict[str, str]]:
        return self.MODELS
    
    def generate_image(
        self,
        prompt: str,
        model: str,
        width: int = 1024,
        height: int = 1024,
        output_dir: Optional[Path] = None
    ) -> str:
        try:
            result = fal_client.subscribe(
                model,
                arguments={
                    "prompt": prompt,
                    "image_size": {"width": width, "height": height},
                    "num_images": 1
                }
            )
            
            image_url = result["images"][0]["url"]
            
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                img_response = requests.get(image_url, timeout=30)
                img_response.raise_for_status()
                
                filename = output_dir / f"img_{hash(prompt) % 10**8}.png"
                with open(filename, 'wb') as f:
                    f.write(img_response.content)
                
                return str(filename)
            
            return image_url
        except Exception as e:
            logger.error(f"Fal.ai error: {e}")
            raise Exception(f"Fal.ai API error: {str(e)}")
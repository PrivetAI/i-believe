import requests
from pathlib import Path
from typing import Optional, List, Dict
import time
import logging

logger = logging.getLogger(__name__)

class BlackForestClient:
    MODELS = [
        {"id": "flux-1.1-pro", "name": "FLUX 1.1 Pro"},
        {"id": "flux-pro", "name": "FLUX Pro"},
        {"id": "flux-dev", "name": "FLUX Dev"},
        {"id": "flux-schnell", "name": "FLUX Schnell"},
    ]
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.bfl.ml"
    
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
            headers = {"x-key": self.api_key}
            payload = {
                "prompt": prompt,
                "width": width,
                "height": height
            }
            
            response = requests.post(
                f"{self.base_url}/v1/{model}",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            task_id = response.json()["id"]
            
            for _ in range(60):
                result = requests.get(
                    f"{self.base_url}/v1/get_result",
                    headers=headers,
                    params={"id": task_id},
                    timeout=10
                )
                result.raise_for_status()
                data = result.json()
                
                if data["status"] == "Ready":
                    image_url = data["result"]["sample"]
                    
                    if output_dir:
                        output_dir.mkdir(parents=True, exist_ok=True)
                        img_response = requests.get(image_url, timeout=30)
                        img_response.raise_for_status()
                        
                        filename = output_dir / f"img_{hash(prompt) % 10**8}.png"
                        with open(filename, 'wb') as f:
                            f.write(img_response.content)
                        
                        return str(filename)
                    
                    return image_url
                
                elif data["status"] == "Error":
                    raise Exception(f"Generation failed: {data}")
                
                time.sleep(2)
            
            raise Exception("Generation timeout")
        except Exception as e:
            logger.error(f"Black Forest Labs error: {e}")
            raise Exception(f"Black Forest Labs API error: {str(e)}")
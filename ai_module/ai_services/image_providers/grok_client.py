import requests
from pathlib import Path
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class GrokClient:
    MODELS = [
        {"id": "grok-2-vision-1212", "name": "Grok 2 Vision"},
        {"id": "grok-vision-beta", "name": "Grok Vision Beta"}
    ]
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.x.ai/v1"
    
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
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Generate an image: {prompt}"
                            }
                        ]
                    }
                ],
                "image": {
                    "size": f"{width}x{height}",
                    "quality": "standard"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            image_url = data["choices"][0]["message"]["content"][0]["image_url"]["url"]
            
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
            logger.error(f"Grok error: {e}")
            raise Exception(f"Grok API error: {str(e)}")
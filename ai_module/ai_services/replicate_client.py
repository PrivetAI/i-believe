import replicate
import requests
from pathlib import Path
from typing import Optional

class ReplicateClient:
    def __init__(self, api_token: str):
        self.client = replicate.Client(api_token=api_token)
    
    def generate_image(
        self,
        prompt: str,
        model: str,
        width: int = 1024,
        height: int = 1024,
        output_dir: Path = None
    ) -> Optional[str]:
        try:
            output = self.client.run(
                model,
                input={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "num_outputs": 1
                }
            )
            
            image_url = output[0] if isinstance(output, list) else output
            
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
            raise Exception(f"Replicate API error: {str(e)}")
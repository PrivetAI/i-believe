from google.cloud import aiplatform
from google.oauth2 import service_account
import base64
from pathlib import Path
from typing import Optional, List, Dict
import json
import logging

logger = logging.getLogger(__name__)

class ImagenClient:
    MODELS = [
        {"id": "imagen-3.0-generate-001", "name": "Imagen 3.0"},
        {"id": "imagen-3.0-fast-generate-001", "name": "Imagen 3.0 Fast"},
    ]
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            credentials_dict = json.loads(api_key)
            credentials = service_account.Credentials.from_service_account_info(credentials_dict)
            aiplatform.init(credentials=credentials, project=credentials_dict.get("project_id"))
            self.initialized = True
        except Exception as e:
            logger.error(f"Imagen init error: {e}")
            self.initialized = False
    
    def get_models(self) -> List[Dict[str, str]]:
        return self.MODELS if self.initialized else []
    
    def generate_image(
        self,
        prompt: str,
        model: str,
        width: int = 1024,
        height: int = 1024,
        output_dir: Optional[Path] = None
    ) -> str:
        if not self.initialized:
            raise Exception("Imagen not initialized. Check API key (Service Account JSON)")
        
        try:
            generation_model = aiplatform.ImageGenerationModel.from_pretrained(model)
            
            response = generation_model.generate_images(
                prompt=prompt,
                number_of_images=1,
                aspect_ratio=f"{width}:{height}" if width == height else "1:1",
            )
            
            image_bytes = response.images[0]._image_bytes
            
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                filename = output_dir / f"img_{hash(prompt) % 10**8}.png"
                with open(filename, 'wb') as f:
                    f.write(image_bytes)
                return str(filename)
            
            return f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"
        except Exception as e:
            logger.error(f"Imagen error: {e}")
            raise Exception(f"Imagen API error: {str(e)}")
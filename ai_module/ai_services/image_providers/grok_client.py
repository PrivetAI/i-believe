import requests
from pathlib import Path
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class GrokClient:
    """Grok Image Generation Client using xAI API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.x.ai/v1"
    
    def get_models(self) -> List[Dict[str, str]]:
        """Получить список доступных моделей генерации изображений"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Фильтруем только модели для генерации изображений
            image_models = [
                {"id": model["id"], "name": model.get("name", model["id"])}
                for model in data.get("data", [])
                if "image" in model["id"].lower() and "grok" in model["id"].lower()
            ]
            
            # Если API не вернул модели, возвращаем известную модель
            if not image_models:
                logger.warning("No image models found via API, using default")
                return [{"id": "grok-2-image-1212", "name": "Grok 2 Image"}]
            
            return sorted(image_models, key=lambda x: x["id"])
            
        except Exception as e:
            logger.error(f"Failed to fetch Grok models: {e}")
            # Fallback на известную модель
            return [{"id": "grok-2-image-1212", "name": "Grok 2 Image"}]
    
    def generate_image(
        self,
        prompt: str,
        model: str,
        width: int = 1024,
        height: int = 768,
        output_dir: Optional[Path] = None
    ) -> str:
        """
        Генерация изображения через xAI API
        
        Note: xAI пока не поддерживает параметры width/height,
        изображения генерируются в фиксированном размере
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            payload = {
                "model": model,
                "prompt": prompt,
                "n": 1,  # Генерируем одно изображение
                "response_format": "url"  # Получаем URL вместо base64
            }
            
            logger.info(f"Generating image with model: {model}")
            logger.debug(f"Prompt: {prompt[:100]}...")
            
            response = requests.post(
                f"{self.base_url}/images/generations",
                headers=headers,
                json=payload,
                timeout=90
            )
            response.raise_for_status()
            data = response.json()
            
            # Получаем URL изображения из ответа
            image_url = data["data"][0]["url"]
            logger.info(f"Image generated successfully: {image_url}")
            
            # Если нужно сохранить локально
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Скачиваем изображение
                img_response = requests.get(image_url, timeout=30)
                img_response.raise_for_status()
                
                # Сохраняем как JPG (xAI возвращает JPG)
                filename = output_dir / f"img_{hash(prompt) % 10**8}.jpg"
                with open(filename, 'wb') as f:
                    f.write(img_response.content)
                
                logger.info(f"Image saved to: {filename}")
                return str(filename)
            
            return image_url
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Grok HTTP error: {e}")
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", str(e))
            except:
                error_msg = str(e)
            raise Exception(f"Grok API error: {error_msg}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Grok request error: {e}")
            raise Exception(f"Grok connection error: {str(e)}")
            
        except (KeyError, IndexError) as e:
            logger.error(f"Grok response parsing error: {e}")
            raise Exception(f"Unexpected Grok response format: {str(e)}")
            
        except Exception as e:
            logger.error(f"Grok error: {e}")
            raise Exception(f"Grok API error: {str(e)}")
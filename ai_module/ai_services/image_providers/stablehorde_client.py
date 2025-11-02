import requests
import time
from pathlib import Path
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class StableHordeClient:
    """Stable Horde API client для генерации изображений"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key or "0000000000"  # Anonymous key if not provided
        self.base_url = "https://stablehorde.net/api/v2"
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
    
    def get_models(self) -> List[Dict[str, str]]:
        """Получить список доступных моделей"""
        try:
            response = requests.get(
                f"{self.base_url}/status/models",
                timeout=30
            )
            response.raise_for_status()
            models_data = response.json()
            
            # Фильтруем только активные image модели
            active_models = [
                {
                    "id": model["name"],
                    "name": f"{model['name']} (queued: {model.get('queued', 0)})"
                }
                for model in models_data
                if model.get("type") == "image" and model.get("count", 0) > 0
            ]
            
            # Сортируем по популярности (меньше в очереди = быстрее)
            active_models.sort(key=lambda x: int(x["name"].split("queued: ")[1].rstrip(")")))
            
            if not active_models:
                logger.warning("No active models found, using defaults")
                return [
                    {"id": "Deliberate", "name": "Deliberate"},
                    {"id": "Realistic Vision", "name": "Realistic Vision"},
                    {"id": "DreamShaper", "name": "DreamShaper"}
                ]
            
            return active_models[:50]  # Ограничиваем до 50 самых быстрых
            
        except Exception as e:
            logger.error(f"Failed to fetch Stable Horde models: {e}")
            return [
                {"id": "Deliberate", "name": "Deliberate (fallback)"},
                {"id": "Realistic Vision", "name": "Realistic Vision (fallback)"}
            ]
    
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
        Генерация изображения через Stable Horde
        
        Args:
            prompt: Текстовый промпт
            model: Название модели
            width: Ширина изображения
            height: Высота изображения
            output_dir: Директория для сохранения
            progress_callback: Функция для обновления прогресса (принимает dict)
        """
        try:
            # Шаг 1: Отправка запроса на генерацию
            logger.info(f"Submitting generation request: model={model}, size={width}x{height}")
            
            payload = {
                "prompt": prompt,
                "params": {
                    "width": width,
                    "height": height,
                    "steps": 25,
                    "cfg_scale": 7.5,
                    "sampler_name": "k_euler_a",
                    "n": 1
                },
                "models": [model],
                "nsfw": False,
                "censor_nsfw": True,
                "r2": True  # Использовать R2 storage для более быстрой загрузки
            }
            
            response = requests.post(
                f"{self.base_url}/generate/async",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if "id" not in data:
                raise Exception(f"Invalid response: {data}")
            
            generation_id = data["id"]
            logger.info(f"Generation queued with ID: {generation_id}")
            
            # Шаг 2: Ожидание завершения с прогресс-баром
            max_wait_time = 600  # 10 минут максимум
            start_time = time.time()
            last_wait_time = None
            
            while time.time() - start_time < max_wait_time:
                check_response = requests.get(
                    f"{self.base_url}/generate/check/{generation_id}",
                    timeout=10
                )
                check_response.raise_for_status()
                status = check_response.json()
                
                wait_time = status.get("wait_time", 0)
                queue_position = status.get("queue_position", 0)
                is_done = status.get("done", False)
                is_faulted = status.get("faulted", False)
                
                # Обновляем прогресс
                if progress_callback:
                    if is_done:
                        progress_callback({
                            "status": "completed",
                            "message": "Generation complete!",
                            "progress": 1.0
                        })
                    elif is_faulted:
                        progress_callback({
                            "status": "failed",
                            "message": "Generation failed",
                            "progress": 0
                        })
                    else:
                        # Рассчитываем примерный прогресс
                        if last_wait_time and wait_time < last_wait_time:
                            progress = 1 - (wait_time / max(last_wait_time, 1))
                        else:
                            progress = 0.1
                        
                        progress_callback({
                            "status": "processing",
                            "message": f"Queue position: {queue_position}, est. wait: {wait_time}s",
                            "progress": min(progress, 0.95),
                            "queue_position": queue_position,
                            "wait_time": wait_time
                        })
                        
                        last_wait_time = wait_time if last_wait_time is None else last_wait_time
                
                if is_faulted:
                    raise Exception("Generation faulted (worker error or timeout)")
                
                if is_done:
                    break
                
                time.sleep(5)  # Проверяем каждые 5 секунд
            else:
                raise Exception(f"Generation timeout after {max_wait_time}s")
            
            # Шаг 3: Получение результата
            result_response = requests.get(
                f"{self.base_url}/generate/status/{generation_id}",
                timeout=30
            )
            result_response.raise_for_status()
            result_data = result_response.json()
            
            if not result_data.get("done") or not result_data.get("generations"):
                raise Exception(f"No generations found: {result_data}")
            
            image_url = result_data["generations"][0]["img"]
            logger.info(f"Image generated: {image_url}")
            
            # Шаг 4: Загрузка и сохранение изображения
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                
                img_response = requests.get(image_url, timeout=60)
                img_response.raise_for_status()
                
                # Определяем расширение из URL или используем png по умолчанию
                ext = "webp" if ".webp" in image_url else "jpg" if ".jpg" in image_url else "png"
                filename = output_dir / f"img_{hash(prompt) % 10**8}.{ext}"
                
                with open(filename, 'wb') as f:
                    f.write(img_response.content)
                
                logger.info(f"Image saved to: {filename}")
                return str(filename)
            
            return image_url
            
        except requests.exceptions.Timeout:
            logger.error("Stable Horde request timeout")
            raise Exception("Stable Horde: Request timeout. Try again later or choose a less busy model.")
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Stable Horde HTTP error: {e}")
            try:
                error_data = e.response.json()
                error_msg = error_data.get("message", str(e))
            except:
                error_msg = str(e)
            raise Exception(f"Stable Horde API error: {error_msg}")
            
        except Exception as e:
            logger.error(f"Stable Horde error: {e}")
            raise Exception(f"Stable Horde error: {str(e)}")
import requests
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class OpenRouterClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
    
    def generate(self, prompt: str, model: str, max_tokens: int = 10000) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens
        }
        
        try:
            logger.info(f"OpenRouter request: model={model}, max_tokens={max_tokens}")
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            
            logger.info(f"OpenRouter status code: {response.status_code}")
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"OpenRouter response: {data}")
            
            return data["choices"][0]["message"]["content"].strip()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"OpenRouter HTTP error: {e}")
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", str(e))
            except:
                error_msg = str(e)
            raise Exception(f"OpenRouter API error: {error_msg}")
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter request error: {e}")
            raise Exception(f"OpenRouter connection error: {str(e)}")
        except KeyError as e:
            logger.error(f"OpenRouter response parsing error: {e}, data: {data}")
            raise Exception(f"OpenRouter unexpected response format: {str(e)}")
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            raise Exception(f"OpenRouter API error: {str(e)}")
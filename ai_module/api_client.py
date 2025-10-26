import requests
import time
from typing import Dict, List, Optional

class VideoGeneratorClient:
    def __init__(self, base_url: str = "http://api:8000/api/v1"):
        self.base_url = base_url
    
    def get_voices(self, language: str = "en-US") -> List[Dict]:
        response = requests.get(f"{self.base_url}/voices", params={"language": language})
        response.raise_for_status()
        return response.json()
    
    def generate_video(
        self,
        slides: List[Dict[str, str]],
        voice: str,
        resolution: str = "9:16"
    ) -> str:
        payload = {
            "slides": slides,
            "voice": voice,
            "resolution": resolution
        }
        
        response = requests.post(f"{self.base_url}/manual/generate", json=payload)
        response.raise_for_status()
        return response.json()["job_id"]
    
    def get_status(self, job_id: str) -> Dict:
        response = requests.get(f"{self.base_url}/status/{job_id}")
        response.raise_for_status()
        return response.json()
    
    def wait_for_completion(self, job_id: str, callback=None) -> Dict:
        while True:
            status = self.get_status(job_id)
            
            if callback:
                callback(status)
            
            if status["status"] == "completed":
                return status
            elif status["status"] == "failed":
                raise Exception(f"Video generation failed: {status.get('error', 'Unknown error')}")
            
            time.sleep(2)
    
    def download_video(self, job_id: str, output_path: str):
        response = requests.get(f"{self.base_url}/download/{job_id}", stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
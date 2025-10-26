import json
import os
from pathlib import Path
from typing import Dict, Optional

PROMPTS_FILE = Path(__file__).parent.parent / "prompts.json"

DEFAULT_PROMPTS = {
    "master": """Create a viral TikTok/Reels video script about {topic}.
Requirements:
- 110-140 words total
- Hook in first 3 seconds
- Emotional storytelling
- Clear structure: Hook → Problem → Solution → CTA
- Conversational tone
- Include power words and curiosity gaps

Output only the script text, no titles or formatting.""",
    
    "split": """Split this video script into 20-25 short segments for slideshow format.

Script:
{script}

Requirements:
- Each segment: 1-2 sentences (5-10 words)
- Logical flow between segments
- Each segment should be visually descriptive
- Maintain narrative coherence
- Output format: JSON array of objects with "text" field

Example output:
[
  {{"text": "Have you ever wondered why?"}},
  {{"text": "The secret lies in timing."}}
]

Output only valid JSON, no markdown or explanations.""",
    
    "image": """Create a detailed image generation prompt for this text segment:
"{text}"

Requirements:
- Cinematic, high-quality photography style
- Specific composition and lighting details
- Emotional mood matching the text
- Avoid text/words in image
- Style: {style}

Output only the image prompt, no explanations."""
}

DEFAULT_MODELS = {
    "text_model": "deepseek/deepseek-r1-distill-qwen-32b",
    "image_model": "stability-ai/sdxl"
}

DEFAULT_STYLES = [
    "Cinematic photography, dramatic lighting",
    "Modern minimalist, clean composition",
    "Vibrant colors, energetic mood",
    "Dark moody atmosphere, film noir",
    "Bright natural light, lifestyle photography"
]

class PromptManager:
    def __init__(self):
        self.prompts_file = PROMPTS_FILE
        self.data = self._load()
    
    def _load(self) -> Dict:
        if self.prompts_file.exists():
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "prompts": DEFAULT_PROMPTS.copy(),
            "models": DEFAULT_MODELS.copy(),
            "styles": DEFAULT_STYLES.copy()
        }
    
    def save(self):
        self.prompts_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.prompts_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def get_prompt(self, key: str) -> str:
        return self.data["prompts"].get(key, "")
    
    def set_prompt(self, key: str, value: str):
        self.data["prompts"][key] = value
        self.save()
    
    def get_model(self, key: str) -> str:
        return self.data["models"].get(key, "")
    
    def set_model(self, key: str, value: str):
        self.data["models"][key] = value
        self.save()
    
    def get_styles(self) -> list:
        return self.data.get("styles", DEFAULT_STYLES.copy())
    
    def add_style(self, style: str):
        if "styles" not in self.data:
            self.data["styles"] = []
        if style not in self.data["styles"]:
            self.data["styles"].append(style)
            self.save()
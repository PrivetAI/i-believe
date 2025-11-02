import google.generativeai as genai
# Используем прямые импорты для читаемости
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.client = genai
        
        # 1. Лучше определить настройки один раз при инициализации
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    
    def get_models(self) -> List[Dict[str, str]]:
        """Получить список доступных моделей"""
        try:
            models = self.client.list_models()
            chat_models = [
                {"id": m.name.replace("models/", ""), "name": m.name.replace("models/", "")}
                for m in models
                if "generateContent" in m.supported_generation_methods
            ]
            return sorted(chat_models, key=lambda x: x["id"])
        except Exception as e:
            # Конкретизируем ошибку
            raise Exception(f"Gemini models fetch error: {str(e)}")
    
    def generate(self, prompt: str, model: str, max_tokens: int = 32768) -> str:
        """
        Генерация текста с использованием best practices.
        Возвращает str, а не Optional[str]. В случае ошибки генерирует исключение.
        """
        try:
            gen_model = self.client.GenerativeModel(model)
            
            # 2. Конфигурация генерации
            generation_config = GenerationConfig(
                max_output_tokens=max_tokens,  # 3. Убрана некорректная логика 'x 3'
                temperature=0.7
            )
            
            response = gen_model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=self.safety_settings
            )
            
            # 4. Главное упрощение: используем 'response.text'
            #
            # SDK `google-generativeai` упрощает нам жизнь:
            # - `response.text` автоматически собирает все 'parts' в одну строку.
            # - Если `finish_reason` = SAFETY или RECITATION, `response.text` 
            #   АВТОМАТИЧЕСКИ вызовет исключение (ValueError).
            # - Если `finish_reason` = MAX_TOKENS, `response.text` вернет 
            #   частичный результат (если он есть).
            
            # 5. Проверяем finish_reason ТОЛЬКО для логирования или особых случаев
            finish_reason = response.candidates[0].finish_reason.name
            
            if finish_reason == "MAX_TOKENS":
                logger.warning(
                    f"MAX_TOKENS ({max_tokens}) reached. "
                    f"Returning partial content (length: {len(response.text)})."
                )
                # Если частичный текст пустой, лучше сообщить об этом
                if not response.text:
                    raise Exception(f"Response truncated: MAX_TOKENS limit ({max_tokens}) reached, but no partial content was returned.")
            
            # `response.text` либо вернет текст, либо вызовет ошибку (которую мы поймаем ниже)
            return response.text.strip()

        except ValueError as e:
            # 6. Этот блок поймает ошибки, которые `response.text` генерирует
            #    при блокировке (SAFETY, RECITATION).
            logger.error(f"Gemini content blocked or response invalid: {e}")
            # Пытаемся получить больше деталей из ответа, если он существует
            try:
                reason = response.candidates[0].finish_reason.name
                ratings = response.candidates[0].safety_ratings
                raise Exception(f"Gemini content blocked. Reason: {reason}. Ratings: {ratings}")
            except (NameError, AttributeError):
                # Если `response` не был определен или не имеет `candidates`
                raise Exception(f"Gemini content blocked or invalid response: {e}")

        except Exception as e:
            # 7. Общий обработчик для других ошибок API
            logger.error(f"Gemini API error in generate(): {str(e)}")
            raise Exception(f"Gemini API error: {str(e)}")
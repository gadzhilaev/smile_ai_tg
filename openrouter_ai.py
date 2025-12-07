import requests
import logging
from typing import List, Dict, Optional
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Keywords that trigger human support request
HUMAN_SUPPORT_KEYWORDS = [
    'оператор', 'человек', 'живой', 'поддержка', 'менеджер',
    'специалист', 'консультант', 'связаться', 'позвонить',
    'operator', 'human', 'support', 'manager', 'agent',
    'real person', 'talk to someone', 'speak to someone'
]

# System prompt for the AI assistant
SYSTEM_PROMPT = """Вы - дружелюбный и полезный AI-ассистент службы поддержки. 
Ваша задача - помогать пользователям с их вопросами и проблемами.

Важные правила:
1. Будьте вежливы и профессиональны
2. Отвечайте на русском языке, если пользователь пишет на русском
3. Если вы не можете помочь с вопросом или пользователь просит связаться с человеком/оператором, 
   скажите что переключаете на оператора поддержки
4. Давайте четкие и конкретные ответы
5. Если вопрос сложный или требует доступа к личным данным пользователя, 
   предложите связаться с оператором

Вы - ассистент компании Smile. Отвечайте кратко и по делу."""


class OpenRouterAI:
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.model = OPENROUTER_MODEL
        self.base_url = OPENROUTER_BASE_URL
        
    def is_human_support_requested(self, message: str) -> bool:
        """Check if user is requesting human support"""
        message_lower = message.lower()
        for keyword in HUMAN_SUPPORT_KEYWORDS:
            if keyword in message_lower:
                return True
        return False
    
    def get_ai_response(self, user_message: str, conversation_history: Optional[List[Dict]] = None) -> Optional[str]:
        """Get AI response from OpenRouter"""
        if not self.api_key:
            logger.error("OpenRouter API key not configured")
            return None
        
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            
            # Add conversation history for context (last 10 messages)
            if conversation_history:
                for msg in conversation_history[-10:]:
                    role = "user" if msg.get("direction") == "user" else "assistant"
                    content = msg.get("message", "")
                    if content:
                        messages.append({"role": role, "content": content})
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://smile-support.com",
                "X-Title": "Smile Support Bot"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_message = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                logger.info(f"AI response generated successfully")
                return ai_message
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("OpenRouter API timeout")
            return None
        except Exception as e:
            logger.error(f"Error getting AI response: {e}")
            return None
    
    def get_human_transfer_message(self) -> str:
        """Message to show when transferring to human support"""
        return "Переключаю вас на оператора поддержки. Пожалуйста, подождите, с вами скоро свяжутся."
    
    def get_ai_unavailable_message(self) -> str:
        """Message to show when AI is unavailable"""
        return "Извините, автоматический ассистент временно недоступен. Переключаю вас на оператора поддержки."


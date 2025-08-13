"""
LLM client for generating reflections and summaries using Gemini Pro
"""
import google.generativeai as genai
import logging
from typing import List, Dict, Optional
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
    
    async def generate_reflection(self, query: str, memories: List[Dict]) -> str:
        """Generate a reflective response based on query and retrieved memories"""
        try:
            # Prepare context from memories
            memory_context = ""
            for i, memory in enumerate(memories[:5], 1):  # Limit to top 5 memories
                timestamp = memory.get('timestamp', 'Unknown time')
                content = memory.get('content', '')
                mood = memory.get('sentiment_analysis', {}).get('mood', 'neutral')
                
                memory_context += f"\nMemory {i} ({timestamp}, mood: {mood}):\n{content}\n"
            
            # Create reflection prompt
            prompt = f"""You are Echoself AI, a reflective personal companion. A user has asked: "{query}"

Based on their personal memories below, provide a thoughtful, empathetic reflection that:
1. Acknowledges their feelings and experiences
2. Offers gentle insights or patterns you notice
3. Provides supportive guidance if appropriate
4. Maintains a warm, understanding tone

Personal Memories:
{memory_context}

Please respond as their caring AI companion, helping them reflect on their experiences and emotions."""

            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating reflection: {e}")
            return "I'm having trouble processing your reflection right now. Please try again later."
    
    async def generate_mood_summary(self, mood_data: Dict, timeframe: str = "recent") -> str:
        """Generate a mood summary report"""
        try:
            prompt = f"""You are Echoself AI, analyzing a user's {timeframe} mood patterns. 

Mood Analysis Data:
- Dominant mood: {mood_data.get('dominant_mood', 'neutral')}
- Mood trend: {mood_data.get('mood_trend', 'stable')}
- Mood distribution: {mood_data.get('mood_distribution', {})}
- Sentiment distribution: {mood_data.get('sentiment_distribution', {})}
- Total messages analyzed: {mood_data.get('total_messages', 0)}

Provide a compassionate, insightful summary that:
1. Highlights key mood patterns
2. Acknowledges emotional trends
3. Offers gentle observations about their emotional journey
4. Suggests self-care or reflection if appropriate
5. Maintains an encouraging, supportive tone

Keep the response personal and caring, as if speaking to a close friend."""

            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating mood summary: {e}")
            return "I'm having trouble analyzing your mood patterns right now. Please try again later."
    
    async def generate_reminder_message(self, reminder_content: str, context: str = "") -> str:
        """Generate a personalized reminder message"""
        try:
            prompt = f"""You are Echoself AI, sending a gentle reminder to a user.

Reminder: {reminder_content}
Context: {context}

Create a warm, personal reminder message that:
1. Gently reminds them of what they wanted to remember
2. Uses an encouraging, supportive tone
3. Feels like a caring friend reminding them
4. Is brief but meaningful

Keep it concise and personal."""

            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating reminder message: {e}")
            return f"Gentle reminder: {reminder_content}"
    
    async def analyze_message_intent(self, message: str) -> Dict:
        """Analyze the intent of an incoming message"""
        try:
            prompt = f"""Analyze this message and determine the user's intent:

Message: "{message}"

Classify the intent as one of:
- reflection_request: User wants to reflect on something or ask for insights
- mood_check: User is sharing their current emotional state
- memory_storage: User is sharing an experience or thought to remember
- reminder_request: User wants to set a reminder
- general_chat: General conversation

Also determine:
- emotional_tone: positive, negative, neutral, mixed
- urgency: low, medium, high
- needs_response: true/false

Respond in JSON format:
{
  "intent": "intent_category",
  "emotional_tone": "tone",
  "urgency": "level",
  "needs_response": boolean,
  "confidence": 0.0-1.0
}"""

            response = self.model.generate_content(prompt)
            # Parse JSON response (simplified - in production, use proper JSON parsing)
            import json
            try:
                return json.loads(response.text)
            except:
                return {
                    "intent": "general_chat",
                    "emotional_tone": "neutral",
                    "urgency": "low",
                    "needs_response": True,
                    "confidence": 0.5
                }
                
        except Exception as e:
            logger.error(f"Error analyzing message intent: {e}")
            return {
                "intent": "general_chat",
                "emotional_tone": "neutral",
                "urgency": "low",
                "needs_response": True,
                "confidence": 0.0
            }
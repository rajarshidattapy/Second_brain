"""
LLM client for generating reflections and summaries using Gemini Pro
"""
import google.generativeai as genai
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio

from config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
            logger.info("LLM client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise RuntimeError(f"LLM client initialization failed: {e}")
    
    async def generate_reflection(self, query: str, memories: List[Dict[str, Any]]) -> str:
        """Generate a reflective response based on query and retrieved memories"""
        try:
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")
            
            # Prepare context from memories
            memory_context = ""
            for i, memory in enumerate(memories[:5], 1):  # Limit to top 5 memories
                timestamp = memory.get('timestamp', 'Unknown time')
                content = memory.get('content', '')
                mood = memory.get('sentiment_analysis', {}).get('mood', 'neutral')
                
                # Truncate very long content
                if len(content) > 300:
                    content = content[:300] + "..."
                
                memory_context += f"\nMemory {i} ({timestamp}, mood: {mood}):\n{content}\n"
            
            if not memory_context.strip():
                return "I don't have any relevant memories to reflect on for your query. Share more of your thoughts and experiences with me so I can provide better insights."
            
            # Create reflection prompt
            prompt = f"""You are Echoself AI, a reflective personal companion. A user has asked: "{query}"

Based on their personal memories below, provide a thoughtful, empathetic reflection that:
1. Acknowledges their feelings and experiences
2. Offers gentle insights or patterns you notice
3. Provides supportive guidance if appropriate
4. Maintains a warm, understanding tone
5. Keeps the response concise but meaningful (2-3 paragraphs max)

Personal Memories:
{memory_context}

Please respond as their caring AI companion, helping them reflect on their experiences and emotions."""

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.model.generate_content(prompt)
            )
            
            if not response or not response.text:
                return "I'm having trouble processing your reflection right now. Please try again later."
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating reflection: {e}")
            return "I'm having trouble processing your reflection right now. Please try again later."
    
    async def generate_mood_summary(self, mood_data: Dict[str, Any], timeframe: str = "recent") -> str:
        """Generate a mood summary report"""
        try:
            if not mood_data:
                return f"I don't have enough data to analyze your mood patterns for the {timeframe} period."
            
            prompt = f"""You are Echoself AI, analyzing a user's {timeframe} mood patterns. 

Mood Analysis Data:
- Dominant mood: {mood_data.get('dominant_mood', 'neutral')}
- Mood trend: {mood_data.get('mood_trend', 'stable')}
- Mood distribution: {mood_data.get('mood_distribution', {})}
- Sentiment distribution: {mood_data.get('sentiment_distribution', {})}
- Total messages analyzed: {mood_data.get('total_messages', 0)}

Provide a compassionate, insightful summary that:
1. Highlights key mood patterns in a positive way
2. Acknowledges emotional trends without being clinical
3. Offers gentle observations about their emotional journey
4. Suggests self-care or reflection if appropriate
5. Maintains an encouraging, supportive tone
6. Keeps the response concise (2-3 paragraphs max)

Keep the response personal and caring, as if speaking to a close friend."""

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.model.generate_content(prompt)
            )
            
            if not response or not response.text:
                return "I'm having trouble analyzing your mood patterns right now. Please try again later."
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating mood summary: {e}")
            return "I'm having trouble analyzing your mood patterns right now. Please try again later."
    
    async def generate_reminder_message(self, reminder_content: str, context: str = "") -> str:
        """Generate a personalized reminder message"""
        try:
            if not reminder_content or not reminder_content.strip():
                return "You have a reminder, but I couldn't retrieve the details."
            
            prompt = f"""You are Echoself AI, sending a gentle reminder to a user.

Reminder: {reminder_content}
Context: {context}

Create a warm, personal reminder message that:
1. Gently reminds them of what they wanted to remember
2. Uses an encouraging, supportive tone
3. Feels like a caring friend reminding them
4. Is brief but meaningful (1-2 sentences max)
5. Includes a gentle emoji if appropriate

Keep it concise and personal."""

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.model.generate_content(prompt)
            )
            
            if not response or not response.text:
                return f"Gentle reminder: {reminder_content} 🔔"
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating reminder message: {e}")
            return f"Gentle reminder: {reminder_content} 🔔"
    
    async def analyze_message_intent(self, message: str) -> Dict[str, Any]:
        """Analyze the intent of an incoming message"""
        try:
            if not message or not message.strip():
                return {
                    "intent": "general_chat",
                    "emotional_tone": "neutral",
                    "urgency": "low",
                    "needs_response": True,
                    "confidence": 0.0
                }
            
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

Respond in valid JSON format only:
{{
  "intent": "intent_category",
  "emotional_tone": "tone",
  "urgency": "level",
  "needs_response": boolean,
  "confidence": 0.0-1.0
}}"""

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.model.generate_content(prompt)
            )
            
            if response and response.text:
                try:
                    import json
                    # Clean the response to extract JSON
                    response_text = response.text.strip()
                    if response_text.startswith('```json'):
                        response_text = response_text[7:]
                    if response_text.endswith('```'):
                        response_text = response_text[:-3]
                    
                    return json.loads(response_text.strip())
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse intent analysis JSON: {response.text}")
            
            # Fallback response
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
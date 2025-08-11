"""
Echoself AI - The Reflective Personal Companion
MCP Server compatible with Puch AI WhatsApp integration
"""
import asyncio
import os
import logging
from typing import Annotated, Optional, List, Dict, Any
from datetime import datetime, timedelta
import json

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp.server.auth.provider import AccessToken
from mcp import ErrorData, McpError
from mcp.types import TextContent, ImageContent, INVALID_PARAMS, INTERNAL_ERROR
from pydantic import BaseModel, Field

# Import our core modules
import sys
sys.path.append('..')
from config import settings
from core.memory_store import MemoryStore
from core.llm_client import LLMClient
from core.whatsapp_handler import WhatsAppHandler
from core.reminder_system import ReminderSystem

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")

assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"

# Auth Provider
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(
                token=token,
                client_id="echoself-client",
                scopes=["*"],
                expires_at=None,
            )
        return None

# Rich Tool Description model
class RichToolDescription(BaseModel):
    description: str
    use_when: str
    side_effects: str | None = None

# Initialize MCP server
mcp = FastMCP(
    "Echoself AI - Reflective Personal Companion",
    auth=SimpleBearerAuthProvider(TOKEN),
)

# Initialize core components
memory_store = MemoryStore()
llm_client = LLMClient()
whatsapp_handler = WhatsAppHandler()
reminder_system = ReminderSystem()

# Tool: validate (required by Puch AI)
@mcp.tool
async def validate() -> str:
    """Validate the MCP server for Puch AI integration"""
    return MY_NUMBER

# Tool: about
@mcp.tool
async def about() -> dict:
    """Get information about Echoself AI"""
    return {
        "name": "Echoself AI",
        "description": "The Reflective Personal Companion - Your AI-powered memory and mood companion",
        "version": "1.0.0",
        "features": [
            "Memory storage and retrieval",
            "Sentiment and mood analysis", 
            "Reflective conversations",
            "Smart reminders",
            "Voice message transcription",
            "Link content extraction"
        ]
    }

# Tool descriptions
STORE_MESSAGE_DESCRIPTION = RichToolDescription(
    description="Store a message (text, audio, image, or link) with sentiment analysis and embeddings",
    use_when="User sends any type of message that should be remembered - thoughts, experiences, voice notes, images, or links",
    side_effects="Creates embeddings, analyzes sentiment/mood, and stores in vector database with metadata"
)

SEARCH_MEMORIES_DESCRIPTION = RichToolDescription(
    description="Search through stored memories and generate reflective insights",
    use_when="User asks questions about their past experiences, wants to reflect, or needs insights from their memories",
    side_effects="Retrieves relevant memories and generates AI-powered reflections using Gemini Pro"
)

SUMMARIZE_MOOD_DESCRIPTION = RichToolDescription(
    description="Analyze mood patterns over a specified time period",
    use_when="User wants to understand their emotional trends, mood patterns, or overall well-being over time",
    side_effects="Analyzes stored sentiment data and generates mood trend reports"
)

SET_REMINDER_DESCRIPTION = RichToolDescription(
    description="Set a reminder using natural language time parsing",
    use_when="User wants to be reminded of something at a specific time or date",
    side_effects="Creates a scheduled reminder that will be sent via WhatsApp at the specified time"
)

GET_REMINDERS_DESCRIPTION = RichToolDescription(
    description="Get all active reminders for the user",
    use_when="User wants to see what reminders they have set",
    side_effects="None - just retrieves existing reminders"
)

# Tool: store_message
@mcp.tool(description=STORE_MESSAGE_DESCRIPTION.model_dump_json())
async def store_message(
    puch_user_id: Annotated[str, Field(description="Puch User Unique Identifier")],
    content: Annotated[str, Field(description="Message content (text, transcription, or description)")],
    message_type: Annotated[str, Field(description="Type of message: text, audio, image, link, document")] = "text",
    metadata: Annotated[Optional[Dict], Field(description="Additional metadata about the message")] = None
) -> List[TextContent]:
    """Store a message with sentiment analysis and embeddings"""
    try:
        if not content or not content.strip():
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Content cannot be empty"))
        
        # Store the memory
        memory_id = await memory_store.store_memory(
            content=content.strip(),
            content_type=message_type,
            metadata={
                **(metadata or {}),
                'user_id': puch_user_id,
                'stored_at': datetime.now().isoformat()
            }
        )
        
        # Get the stored memory for response
        memories = await memory_store.search_memories(content, limit=1)
        if memories:
            memory = memories[0]
            sentiment = memory.sentiment_analysis
            
            response = {
                "memory_id": memory_id,
                "message": "Memory stored successfully",
                "sentiment_analysis": {
                    "sentiment": sentiment.get('sentiment', 'neutral'),
                    "mood": sentiment.get('mood', 'neutral'),
                    "emotions": sentiment.get('emotions', []),
                    "confidence": sentiment.get('confidence', 0.0)
                },
                "content_type": message_type
            }
        else:
            response = {
                "memory_id": memory_id,
                "message": "Memory stored successfully",
                "content_type": message_type
            }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except McpError:
        raise
    except Exception as e:
        logger.error(f"Error storing message: {e}")
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))

# Tool: search_memories
@mcp.tool(description=SEARCH_MEMORIES_DESCRIPTION.model_dump_json())
async def search_memories(
    puch_user_id: Annotated[str, Field(description="Puch User Unique Identifier")],
    query: Annotated[str, Field(description="Natural language query to search memories")],
    limit: Annotated[int, Field(description="Maximum number of memories to retrieve")] = 5,
    filters: Annotated[Optional[Dict], Field(description="Optional filters (sentiment, mood, content_type)")] = None
) -> List[TextContent]:
    """Search memories and generate reflective insights"""
    try:
        if not query or not query.strip():
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Query cannot be empty"))
        
        # Add user filter
        search_filters = filters or {}
        # Note: In a real implementation, you'd filter by user_id in the vector DB
        
        # Search for relevant memories
        memories = await memory_store.search_memories(query.strip(), limit=limit, filters=search_filters)
        
        if not memories:
            return [TextContent(type="text", text="I couldn't find any relevant memories for your query. Try asking about something else or share more experiences with me first.")]
        
        # Convert memories to dict format for LLM
        memory_dicts = []
        for memory in memories:
            memory_dicts.append({
                'content': memory.content,
                'timestamp': memory.timestamp.isoformat(),
                'sentiment_analysis': memory.sentiment_analysis,
                'content_type': memory.content_type
            })
        
        # Generate reflection using LLM
        reflection = await llm_client.generate_reflection(query, memory_dicts)
        
        # Prepare response
        response = {
            "reflection": reflection,
            "memories_found": len(memories),
            "query": query,
            "relevant_memories": [
                {
                    "content": memory.content[:200] + "..." if len(memory.content) > 200 else memory.content,
                    "timestamp": memory.timestamp.isoformat(),
                    "mood": memory.sentiment_analysis.get('mood', 'neutral')
                }
                for memory in memories[:3]  # Show top 3 memories
            ]
        }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except McpError:
        raise
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))

# Tool: summarize_mood
@mcp.tool(description=SUMMARIZE_MOOD_DESCRIPTION.model_dump_json())
async def summarize_mood(
    puch_user_id: Annotated[str, Field(description="Puch User Unique Identifier")],
    days: Annotated[int, Field(description="Number of days to analyze")] = 7
) -> List[TextContent]:
    """Analyze mood patterns over a specified time period"""
    try:
        if days <= 0 or days > 365:
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Days must be between 1 and 365"))
        
        # Get mood summary from memory store
        mood_data = await memory_store.get_mood_summary(days=days)
        
        if not mood_data or mood_data.get('total_messages', 0) == 0:
            return [TextContent(type="text", text=f"I don't have enough data to analyze your mood over the last {days} days. Share more of your thoughts and experiences with me!")]
        
        # Generate mood summary using LLM
        timeframe = f"last {days} days" if days > 1 else "today"
        mood_summary = await llm_client.generate_mood_summary(mood_data, timeframe)
        
        # Prepare detailed response
        response = {
            "mood_summary": mood_summary,
            "analysis_period": f"{days} days",
            "statistics": {
                "total_messages": mood_data.get('total_messages', 0),
                "dominant_mood": mood_data.get('dominant_mood', 'neutral'),
                "mood_trend": mood_data.get('mood_trend', 'stable'),
                "mood_distribution": mood_data.get('mood_distribution', {}),
                "sentiment_distribution": mood_data.get('sentiment_distribution', {})
            }
        }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except McpError:
        raise
    except Exception as e:
        logger.error(f"Error summarizing mood: {e}")
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))

# Tool: set_reminder
@mcp.tool(description=SET_REMINDER_DESCRIPTION.model_dump_json())
async def set_reminder(
    puch_user_id: Annotated[str, Field(description="Puch User Unique Identifier")],
    content: Annotated[str, Field(description="What to remind about")],
    time_text: Annotated[str, Field(description="When to remind (natural language: 'tomorrow at 9am', 'in 2 hours', etc.)")],
    metadata: Annotated[Optional[Dict], Field(description="Additional metadata for the reminder")] = None
) -> List[TextContent]:
    """Set a reminder using natural language time parsing"""
    try:
        if not content or not content.strip():
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Reminder content cannot be empty"))
        
        if not time_text or not time_text.strip():
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Time specification cannot be empty"))
        
        # Create the reminder
        reminder_id = await reminder_system.create_reminder(
            user_id=puch_user_id,
            content=content.strip(),
            time_text=time_text.strip(),
            metadata=metadata
        )
        
        if not reminder_id:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Could not parse time: '{time_text}'. Try formats like 'tomorrow at 9am', 'in 2 hours', or 'next Monday at 3pm'"))
        
        # Get the created reminder for confirmation
        user_reminders = await reminder_system.get_user_reminders(puch_user_id)
        created_reminder = next((r for r in user_reminders if r.id == reminder_id), None)
        
        if created_reminder:
            response = {
                "message": "Reminder set successfully!",
                "reminder_id": reminder_id,
                "content": content.strip(),
                "scheduled_time": created_reminder.scheduled_time.isoformat(),
                "time_until_reminder": str(created_reminder.scheduled_time - datetime.now())
            }
        else:
            response = {
                "message": "Reminder set successfully!",
                "reminder_id": reminder_id,
                "content": content.strip()
            }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except McpError:
        raise
    except Exception as e:
        logger.error(f"Error setting reminder: {e}")
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))

# Tool: get_reminders
@mcp.tool(description=GET_REMINDERS_DESCRIPTION.model_dump_json())
async def get_reminders(
    puch_user_id: Annotated[str, Field(description="Puch User Unique Identifier")],
    include_sent: Annotated[bool, Field(description="Include already sent reminders")] = False
) -> List[TextContent]:
    """Get all reminders for the user"""
    try:
        reminders = await reminder_system.get_user_reminders(puch_user_id, include_sent=include_sent)
        
        if not reminders:
            message = "You don't have any active reminders." if not include_sent else "You don't have any reminders."
            return [TextContent(type="text", text=message)]
        
        reminder_list = []
        for reminder in reminders:
            time_until = reminder.scheduled_time - datetime.now()
            status = "sent" if reminder.is_sent else "pending"
            
            reminder_info = {
                "id": reminder.id,
                "content": reminder.content,
                "scheduled_time": reminder.scheduled_time.isoformat(),
                "status": status,
                "created_at": reminder.created_at.isoformat()
            }
            
            if not reminder.is_sent and time_until.total_seconds() > 0:
                reminder_info["time_until"] = str(time_until)
            
            reminder_list.append(reminder_info)
        
        response = {
            "total_reminders": len(reminders),
            "active_reminders": len([r for r in reminders if not r.is_sent]),
            "reminders": reminder_list
        }
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Error getting reminders: {e}")
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=str(e)))

# Reminder callback for WhatsApp notifications
async def reminder_callback(reminder):
    """Send reminder via WhatsApp"""
    try:
        # Generate personalized reminder message
        reminder_message = await llm_client.generate_reminder_message(
            reminder.content,
            context=f"Reminder set on {reminder.created_at.strftime('%Y-%m-%d')}"
        )
        
        # In a real implementation, you would send this via WhatsApp
        # For now, we'll just log it
        logger.info(f"Reminder for user {reminder.user_id}: {reminder_message}")
        
        # You could integrate with Puch AI here to send the actual WhatsApp message
        # await whatsapp_handler.send_message(reminder.user_id, reminder_message)
        
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")

# Register reminder callback
reminder_system.add_reminder_callback(reminder_callback)

# Run MCP Server
async def main():
    print("🧠 Starting Echoself AI MCP Server on http://0.0.0.0:8086")
    print("🔗 Ready for Puch AI WhatsApp integration")
    print("📱 Connect via: /mcp connect <your-https-url> <your-bearer-token>")
    
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)

if __name__ == "__main__":
    asyncio.run(main())
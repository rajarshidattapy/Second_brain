"""
WhatsApp message handling via Puch AI
"""
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import whisper
import tempfile
import os
from urllib.parse import urlparse
import mimetypes

from config import settings

logger = logging.getLogger(__name__)

class WhatsAppHandler:
    def __init__(self):
        self.base_url = settings.PUCH_AI_BASE_URL
        self.token = settings.PUCH_AI_TOKEN
        self.user_phone = settings.PUCH_USER_PHONE
        self.whisper_model = whisper.load_model(settings.WHISPER_MODEL)
        
        # Headers for API requests
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    async def send_message(self, phone_number: str, message: str, message_type: str = 'text') -> bool:
        """Send a message via Puch AI"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'phone': phone_number,
                    'message': message,
                    'type': message_type
                }
                
                async with session.post(
                    f"{self.base_url}/messages/send",
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        logger.info(f"Message sent successfully to {phone_number}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send message: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    async def get_messages(self, limit: int = 50) -> List[Dict]:
        """Get recent messages from Puch AI"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'limit': limit,
                    'phone': self.user_phone
                }
                
                async with session.get(
                    f"{self.base_url}/messages",
                    params=params,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('messages', [])
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get messages: {response.status} - {error_text}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []
    
    async def download_media(self, media_url: str) -> Optional[bytes]:
        """Download media file from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(media_url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Failed to download media: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            return None
    
    async def transcribe_audio(self, audio_data: bytes, filename: str = "audio.ogg") -> Optional[str]:
        """Transcribe audio using Whisper"""
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # Transcribe using Whisper
                result = self.whisper_model.transcribe(temp_file_path)
                transcription = result['text'].strip()
                
                logger.info(f"Audio transcribed successfully: {len(transcription)} characters")
                return transcription
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
    
    async def extract_link_content(self, url: str) -> Optional[str]:
        """Extract content from a shared link"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        
                        if 'text/html' in content_type:
                            html_content = await response.text()
                            # Simple text extraction (in production, use BeautifulSoup)
                            import re
                            text_content = re.sub(r'<[^>]+>', ' ', html_content)
                            text_content = re.sub(r'\s+', ' ', text_content).strip()
                            
                            # Limit content length
                            if len(text_content) > 1000:
                                text_content = text_content[:1000] + "..."
                            
                            return f"Link content from {url}: {text_content}"
                        else:
                            return f"Link shared: {url} (Content type: {content_type})"
                    else:
                        return f"Link shared: {url} (Could not fetch content)"
                        
        except Exception as e:
            logger.error(f"Error extracting link content: {e}")
            return f"Link shared: {url}"
    
    async def process_message(self, message: Dict) -> Dict:
        """Process incoming message and extract content"""
        try:
            message_type = message.get('type', 'text')
            content = ""
            metadata = {
                'original_message': message,
                'processed_at': datetime.now().isoformat(),
                'from_phone': message.get('from', ''),
                'message_id': message.get('id', '')
            }
            
            if message_type == 'text':
                content = message.get('text', '')
                
                # Check for URLs in text
                import re
                urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
                if urls:
                    # Extract content from first URL
                    link_content = await self.extract_link_content(urls[0])
                    if link_content:
                        content += f"\n\n{link_content}"
                        metadata['extracted_links'] = urls
            
            elif message_type == 'audio' or message_type == 'voice':
                # Download and transcribe audio
                media_url = message.get('media_url', '')
                if media_url:
                    audio_data = await self.download_media(media_url)
                    if audio_data:
                        transcription = await self.transcribe_audio(audio_data)
                        if transcription:
                            content = f"[Voice message transcription]: {transcription}"
                            metadata['transcription'] = transcription
                            metadata['original_media_url'] = media_url
                        else:
                            content = "[Voice message - transcription failed]"
                    else:
                        content = "[Voice message - download failed]"
                else:
                    content = "[Voice message - no media URL]"
            
            elif message_type == 'image':
                # For images, we'll create a simple caption
                # In production, you might want to use image captioning AI
                media_url = message.get('media_url', '')
                caption = message.get('caption', '')
                
                if caption:
                    content = f"[Image with caption]: {caption}"
                else:
                    content = "[Image shared]"
                
                metadata['media_url'] = media_url
                metadata['caption'] = caption
            
            elif message_type == 'document':
                filename = message.get('filename', 'document')
                caption = message.get('caption', '')
                
                if caption:
                    content = f"[Document '{filename}' with caption]: {caption}"
                else:
                    content = f"[Document shared: {filename}]"
                
                metadata['filename'] = filename
                metadata['media_url'] = message.get('media_url', '')
            
            else:
                content = f"[{message_type.title()} message]"
                if 'text' in message:
                    content += f": {message['text']}"
            
            return {
                'content': content,
                'content_type': message_type,
                'metadata': metadata,
                'timestamp': message.get('timestamp', datetime.now().isoformat())
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'content': f"[Error processing {message.get('type', 'unknown')} message]",
                'content_type': 'error',
                'metadata': {'error': str(e)},
                'timestamp': datetime.now().isoformat()
            }
    
    async def send_typing_indicator(self, phone_number: str):
        """Send typing indicator"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'phone': phone_number,
                    'action': 'typing'
                }
                
                async with session.post(
                    f"{self.base_url}/messages/action",
                    json=payload,
                    headers=self.headers
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Error sending typing indicator: {e}")
            return False
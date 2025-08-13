"""
Memory storage and retrieval using Qdrant vector database
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import logging

from config import settings
from core.encryption import MemoryEncryption
from core.sentiment_analyzer import SentimentAnalyzer, SentimentResult

logger = logging.getLogger(__name__)

@dataclass
class Memory:
    id: str
    content: str
    content_type: str  # text, voice_transcript, image_caption, link_summary
    timestamp: datetime
    sentiment_analysis: Dict
    metadata: Dict
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Memory':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

class MemoryStore:
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.sentiment_analyzer = SentimentAnalyzer()
        self.encryption = MemoryEncryption(settings.ENCRYPTION_KEY)
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        
        # Initialize collection
        asyncio.create_task(self._initialize_collection())
    
    async def _initialize_collection(self):
        """Initialize Qdrant collection if it doesn't exist"""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Get embedding dimension
                sample_embedding = self.embedding_model.encode(["sample text"])
                embedding_dim = len(sample_embedding[0])
                
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Qdrant collection already exists: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")
    
    def _create_embedding(self, text: str) -> List[float]:
        """Create embedding for text"""
        try:
            embedding = self.embedding_model.encode([text])
            return embedding[0].tolist()
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            return []
    
    async def store_memory(self, content: str, content_type: str, metadata: Dict = None) -> str:
        """Store a new memory"""
        try:
            # Generate unique ID
            memory_id = str(uuid.uuid4())
            
            # Analyze sentiment
            sentiment_result = self.sentiment_analyzer.analyze_sentiment(content)
            sentiment_data = {
                'sentiment': sentiment_result.sentiment,
                'mood': sentiment_result.mood,
                'confidence': sentiment_result.confidence,
                'emotions': sentiment_result.emotions,
                'intensity': sentiment_result.intensity
            }
            
            # Create embedding
            embedding = self._create_embedding(content)
            
            # Create memory object
            memory = Memory(
                id=memory_id,
                content=content,
                content_type=content_type,
                timestamp=datetime.now(),
                sentiment_analysis=sentiment_data,
                metadata=metadata or {},
                embedding=embedding
            )
            
            # Encrypt sensitive content
            encrypted_content = self.encryption.encrypt_data(content)
            encrypted_metadata = self.encryption.encrypt_json(metadata or {})
            
            # Store in Qdrant
            point = PointStruct(
                id=memory_id,
                vector=embedding,
                payload={
                    'content_type': content_type,
                    'timestamp': memory.timestamp.isoformat(),
                    'sentiment': sentiment_data['sentiment'],
                    'mood': sentiment_data['mood'],
                    'emotions': sentiment_data['emotions'],
                    'intensity': sentiment_data['intensity'],
                    'confidence': sentiment_data['confidence'],
                    'encrypted_content': encrypted_content,
                    'encrypted_metadata': encrypted_metadata
                }
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Stored memory: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise
    
    async def search_memories(self, query: str, limit: int = 10, filters: Dict = None) -> List[Memory]:
        """Search for relevant memories"""
        try:
            # Create query embedding
            query_embedding = self._create_embedding(query)
            
            # Build filter conditions
            filter_conditions = []
            if filters:
                for key, value in filters.items():
                    if key == 'sentiment':
                        filter_conditions.append(
                            models.FieldCondition(
                                key='sentiment',
                                match=models.MatchValue(value=value)
                            )
                        )
                    elif key == 'mood':
                        filter_conditions.append(
                            models.FieldCondition(
                                key='mood',
                                match=models.MatchValue(value=value)
                            )
                        )
                    elif key == 'content_type':
                        filter_conditions.append(
                            models.FieldCondition(
                                key='content_type',
                                match=models.MatchValue(value=value)
                            )
                        )
            
            # Search
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=models.Filter(must=filter_conditions) if filter_conditions else None,
                limit=limit,
                with_payload=True
            )
            
            # Decrypt and convert results
            memories = []
            for result in search_result:
                try:
                    payload = result.payload
                    
                    # Decrypt content and metadata
                    decrypted_content = self.encryption.decrypt_data(payload['encrypted_content'])
                    decrypted_metadata = self.encryption.decrypt_json(payload['encrypted_metadata'])
                    
                    memory = Memory(
                        id=result.id,
                        content=decrypted_content,
                        content_type=payload['content_type'],
                        timestamp=datetime.fromisoformat(payload['timestamp']),
                        sentiment_analysis={
                            'sentiment': payload['sentiment'],
                            'mood': payload['mood'],
                            'emotions': payload['emotions'],
                            'intensity': payload['intensity'],
                            'confidence': payload['confidence']
                        },
                        metadata=decrypted_metadata
                    )
                    memories.append(memory)
                    
                except Exception as e:
                    logger.error(f"Failed to decrypt memory {result.id}: {e}")
                    continue
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def get_recent_memories(self, limit: int = 20) -> List[Memory]:
        """Get recent memories"""
        try:
            # Get all points and sort by timestamp
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                with_payload=True
            )
            
            memories = []
            for point in scroll_result[0]:
                try:
                    payload = point.payload
                    
                    # Decrypt content and metadata
                    decrypted_content = self.encryption.decrypt_data(payload['encrypted_content'])
                    decrypted_metadata = self.encryption.decrypt_json(payload['encrypted_metadata'])
                    
                    memory = Memory(
                        id=point.id,
                        content=decrypted_content,
                        content_type=payload['content_type'],
                        timestamp=datetime.fromisoformat(payload['timestamp']),
                        sentiment_analysis={
                            'sentiment': payload['sentiment'],
                            'mood': payload['mood'],
                            'emotions': payload['emotions'],
                            'intensity': payload['intensity'],
                            'confidence': payload['confidence']
                        },
                        metadata=decrypted_metadata
                    )
                    memories.append(memory)
                    
                except Exception as e:
                    logger.error(f"Failed to decrypt memory {point.id}: {e}")
                    continue
            
            # Sort by timestamp (most recent first)
            memories.sort(key=lambda m: m.timestamp, reverse=True)
            return memories[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get recent memories: {e}")
            return []
    
    async def get_mood_summary(self, days: int = 7) -> Dict:
        """Get mood summary for the last N days"""
        try:
            # Get recent memories
            memories = await self.get_recent_memories(limit=1000)
            
            # Filter by date range
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            recent_memories = [
                m for m in memories 
                if m.timestamp >= cutoff_date
            ]
            
            # Convert to dict format for analysis
            memory_dicts = [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'sentiment_analysis': m.sentiment_analysis
                }
                for m in recent_memories
            ]
            
            return self.sentiment_analyzer.analyze_mood_patterns(memory_dicts)
            
        except Exception as e:
            logger.error(f"Failed to get mood summary: {e}")
            return {}
    
    async def export_memories(self) -> Dict:
        """Export all memories for backup"""
        try:
            memories = await self.get_recent_memories(limit=10000)  # Get all
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'total_memories': len(memories),
                'memories': [memory.to_dict() for memory in memories]
            }
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export memories: {e}")
            return {}
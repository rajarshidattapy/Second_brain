"""
Memory storage and retrieval using Qdrant vector database with user isolation
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import logging

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from config import settings
from core.encryption import MemoryEncryption
from core.sentiment_analyzer import SentimentAnalyzer, SentimentResult

logger = logging.getLogger(__name__)

@dataclass
class Memory:
    id: str
    user_id: str
    content: str
    content_type: str  # text, voice_transcript, image_caption, link_summary
    timestamp: datetime
    sentiment_analysis: Dict[str, Any]
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

class MemoryStore:
    def __init__(self):
        self.client = None
        self.embedding_model = None
        self.sentiment_analyzer = SentimentAnalyzer()
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self._user_encryptions: Dict[str, MemoryEncryption] = {}
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure the memory store is properly initialized"""
        if self._initialized:
            return
        
        try:
            # Initialize Qdrant client
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            
            # Initialize collection
            await self._initialize_collection()
            
            self._initialized = True
            logger.info("Memory store initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory store: {e}")
            raise RuntimeError(f"Memory store initialization failed: {e}")
    
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
                
                # Create index for user_id field for efficient filtering
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="user_id",
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
                
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Qdrant collection already exists: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")
            raise
    
    def _get_user_encryption(self, user_id: str) -> MemoryEncryption:
        """Get or create encryption instance for user"""
        if user_id not in self._user_encryptions:
            user_salt = MemoryEncryption.generate_user_salt(user_id)
            self._user_encryptions[user_id] = MemoryEncryption(
                password=settings.ENCRYPTION_KEY,
                salt=user_salt
            )
        return self._user_encryptions[user_id]
    
    def _create_embedding(self, text: str) -> List[float]:
        """Create embedding for text"""
        try:
            if not self.embedding_model:
                raise RuntimeError("Embedding model not initialized")
            
            embedding = self.embedding_model.encode([text])
            return embedding[0].tolist()
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            raise ValueError(f"Embedding creation failed: {e}")
    
    async def store_memory(self, user_id: str, content: str, content_type: str, metadata: Dict[str, Any] = None) -> str:
        """Store a new memory with user isolation"""
        await self._ensure_initialized()
        
        try:
            if not content or not content.strip():
                raise ValueError("Content cannot be empty")
            
            if not user_id or not user_id.strip():
                raise ValueError("User ID cannot be empty")
            
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
            
            # Get user-specific encryption
            encryption = self._get_user_encryption(user_id)
            
            # Encrypt sensitive content
            encrypted_content = encryption.encrypt_data(content)
            encrypted_metadata = encryption.encrypt_json(metadata or {})
            
            # Store in Qdrant with user isolation
            point = PointStruct(
                id=memory_id,
                vector=embedding,
                payload={
                    'user_id': user_id,  # Critical for user isolation
                    'content_type': content_type,
                    'timestamp': datetime.now().isoformat(),
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
            
            logger.info(f"Stored memory {memory_id} for user {user_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to store memory for user {user_id}: {e}")
            raise RuntimeError(f"Memory storage failed: {e}")
    
    async def search_memories(self, user_id: str, query: str, limit: int = 10, filters: Dict[str, Any] = None) -> List[Memory]:
        """Search for relevant memories with user isolation"""
        await self._ensure_initialized()
        
        try:
            if not user_id or not user_id.strip():
                raise ValueError("User ID cannot be empty")
            
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")
            
            # Create query embedding
            query_embedding = self._create_embedding(query)
            
            # Build filter conditions with user isolation
            filter_conditions = [
                FieldCondition(
                    key='user_id',
                    match=MatchValue(value=user_id)
                )
            ]
            
            # Add additional filters
            if filters:
                for key, value in filters.items():
                    if key in ['sentiment', 'mood', 'content_type']:
                        filter_conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=value)
                            )
                        )
            
            # Search with user isolation
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=Filter(must=filter_conditions),
                limit=limit,
                with_payload=True
            )
            
            # Decrypt and convert results
            memories = []
            encryption = self._get_user_encryption(user_id)
            
            for result in search_result:
                try:
                    payload = result.payload
                    
                    # Verify user isolation
                    if payload.get('user_id') != user_id:
                        logger.warning(f"User isolation breach detected for memory {result.id}")
                        continue
                    
                    # Decrypt content and metadata
                    decrypted_content = encryption.decrypt_data(payload['encrypted_content'])
                    decrypted_metadata = encryption.decrypt_json(payload['encrypted_metadata'])
                    
                    memory = Memory(
                        id=str(result.id),
                        user_id=user_id,
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
                    logger.error(f"Failed to decrypt memory {result.id} for user {user_id}: {e}")
                    continue
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search memories for user {user_id}: {e}")
            raise RuntimeError(f"Memory search failed: {e}")
    
    async def get_recent_memories(self, user_id: str, limit: int = 20) -> List[Memory]:
        """Get recent memories for a specific user"""
        await self._ensure_initialized()
        
        try:
            if not user_id or not user_id.strip():
                raise ValueError("User ID cannot be empty")
            
            # Scroll with user filter
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key='user_id',
                            match=MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True
            )
            
            memories = []
            encryption = self._get_user_encryption(user_id)
            
            for point in scroll_result[0]:
                try:
                    payload = point.payload
                    
                    # Verify user isolation
                    if payload.get('user_id') != user_id:
                        logger.warning(f"User isolation breach detected for memory {point.id}")
                        continue
                    
                    # Decrypt content and metadata
                    decrypted_content = encryption.decrypt_data(payload['encrypted_content'])
                    decrypted_metadata = encryption.decrypt_json(payload['encrypted_metadata'])
                    
                    memory = Memory(
                        id=str(point.id),
                        user_id=user_id,
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
                    logger.error(f"Failed to decrypt memory {point.id} for user {user_id}: {e}")
                    continue
            
            # Sort by timestamp (most recent first)
            memories.sort(key=lambda m: m.timestamp, reverse=True)
            return memories[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get recent memories for user {user_id}: {e}")
            raise RuntimeError(f"Recent memories retrieval failed: {e}")
    
    async def get_mood_summary(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get mood summary for a specific user over the last N days"""
        try:
            if not user_id or not user_id.strip():
                raise ValueError("User ID cannot be empty")
            
            # Get recent memories for the user
            memories = await self.get_recent_memories(user_id, limit=1000)
            
            # Filter by date range
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            from datetime import timedelta
            cutoff_date = cutoff_date - timedelta(days=days)
            
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
            logger.error(f"Failed to get mood summary for user {user_id}: {e}")
            raise RuntimeError(f"Mood summary failed: {e}")
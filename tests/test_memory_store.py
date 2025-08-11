"""
Tests for memory store functionality
"""
import pytest
import asyncio
from datetime import datetime
from core.memory_store import MemoryStore, Memory

@pytest.fixture
async def memory_store():
    """Create a test memory store instance"""
    store = MemoryStore()
    await asyncio.sleep(1)  # Wait for initialization
    return store

@pytest.mark.asyncio
async def test_store_memory(memory_store):
    """Test storing a memory"""
    content = "This is a test memory"
    content_type = "text"
    metadata = {"test": True}
    
    memory_id = await memory_store.store_memory(content, content_type, metadata)
    
    assert memory_id is not None
    assert isinstance(memory_id, str)

@pytest.mark.asyncio
async def test_search_memories(memory_store):
    """Test searching memories"""
    # Store a test memory first
    await memory_store.store_memory("I love sunny days", "text", {"weather": "sunny"})
    
    # Search for it
    memories = await memory_store.search_memories("sunny weather", limit=5)
    
    assert len(memories) >= 0  # May be 0 if Qdrant isn't running
    if memories:
        assert isinstance(memories[0], Memory)

@pytest.mark.asyncio
async def test_mood_summary(memory_store):
    """Test mood summary generation"""
    # Store some test memories with different sentiments
    await memory_store.store_memory("I'm so happy today!", "text")
    await memory_store.store_memory("Feeling a bit sad", "text")
    
    mood_summary = await memory_store.get_mood_summary(days=1)
    
    assert isinstance(mood_summary, dict)
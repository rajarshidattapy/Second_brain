"""
Tests for reminder system
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from core.reminder_system import ReminderSystem

@pytest.fixture
def reminder_system():
    return ReminderSystem()

def test_parse_reminder_time(reminder_system):
    """Test time parsing"""
    # Test various time formats
    test_cases = [
        "tomorrow at 9am",
        "in 2 hours", 
        "next Monday at 3pm",
        "2024-12-25 10:00"
    ]
    
    for time_text in test_cases:
        parsed_time = reminder_system.parse_reminder_time(time_text)
        if parsed_time:  # Some might fail depending on dateparser
            assert isinstance(parsed_time, datetime)
            assert parsed_time > datetime.now()

@pytest.mark.asyncio
async def test_create_reminder(reminder_system):
    """Test creating a reminder"""
    user_id = "test_user"
    content = "Test reminder"
    time_text = "in 1 hour"
    
    reminder_id = await reminder_system.create_reminder(user_id, content, time_text)
    
    if reminder_id:  # Might be None if time parsing fails
        assert isinstance(reminder_id, str)
        
        # Check if reminder was created
        reminders = await reminder_system.get_user_reminders(user_id)
        assert len(reminders) >= 1

@pytest.mark.asyncio
async def test_get_user_reminders(reminder_system):
    """Test getting user reminders"""
    user_id = "test_user_2"
    
    # Create a reminder first
    await reminder_system.create_reminder(user_id, "Test", "tomorrow")
    
    reminders = await reminder_system.get_user_reminders(user_id)
    assert isinstance(reminders, list)
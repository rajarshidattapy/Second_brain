"""
Reminder system for scheduling and managing user reminders
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import dateparser
import logging
from dataclasses import dataclass, asdict

from config import settings

logger = logging.getLogger(__name__)

@dataclass
class Reminder:
    id: str
    user_id: str
    content: str
    scheduled_time: datetime
    created_at: datetime
    is_sent: bool = False
    metadata: Dict = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['scheduled_time'] = self.scheduled_time.isoformat()
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Reminder':
        data['scheduled_time'] = datetime.fromisoformat(data['scheduled_time'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)

class ReminderSystem:
    def __init__(self):
        self.reminders: Dict[str, Reminder] = {}
        self.reminder_callbacks = []
        self._load_reminders()
        
        # Start background task for checking reminders
        asyncio.create_task(self._reminder_checker())
    
    def _load_reminders(self):
        """Load reminders from storage"""
        try:
            import os
            reminders_file = os.path.join(settings.DATA_DIR, "reminders.json")
            if os.path.exists(reminders_file):
                with open(reminders_file, 'r') as f:
                    data = json.load(f)
                    for reminder_data in data.get('reminders', []):
                        reminder = Reminder.from_dict(reminder_data)
                        self.reminders[reminder.id] = reminder
                logger.info(f"Loaded {len(self.reminders)} reminders")
        except Exception as e:
            logger.error(f"Error loading reminders: {e}")
    
    def _save_reminders(self):
        """Save reminders to storage"""
        try:
            import os
            reminders_file = os.path.join(settings.DATA_DIR, "reminders.json")
            data = {
                'reminders': [reminder.to_dict() for reminder in self.reminders.values()],
                'last_updated': datetime.now().isoformat()
            }
            with open(reminders_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving reminders: {e}")
    
    def parse_reminder_time(self, time_text: str) -> Optional[datetime]:
        """Parse natural language time into datetime"""
        try:
            # Use dateparser to handle natural language
            parsed_time = dateparser.parse(
                time_text,
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'RETURN_AS_TIMEZONE_AWARE': False
                }
            )
            
            if parsed_time:
                # If the parsed time is in the past, assume it's for tomorrow
                if parsed_time < datetime.now():
                    parsed_time += timedelta(days=1)
                
                return parsed_time
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing time '{time_text}': {e}")
            return None
    
    async def create_reminder(self, user_id: str, content: str, time_text: str, metadata: Dict = None) -> Optional[str]:
        """Create a new reminder"""
        try:
            scheduled_time = self.parse_reminder_time(time_text)
            if not scheduled_time:
                return None
            
            reminder_id = str(uuid.uuid4())
            reminder = Reminder(
                id=reminder_id,
                user_id=user_id,
                content=content,
                scheduled_time=scheduled_time,
                created_at=datetime.now(),
                metadata=metadata or {}
            )
            
            self.reminders[reminder_id] = reminder
            self._save_reminders()
            
            logger.info(f"Created reminder {reminder_id} for {scheduled_time}")
            return reminder_id
            
        except Exception as e:
            logger.error(f"Error creating reminder: {e}")
            return None
    
    async def get_user_reminders(self, user_id: str, include_sent: bool = False) -> List[Reminder]:
        """Get all reminders for a user"""
        try:
            user_reminders = [
                reminder for reminder in self.reminders.values()
                if reminder.user_id == user_id and (include_sent or not reminder.is_sent)
            ]
            
            # Sort by scheduled time
            user_reminders.sort(key=lambda r: r.scheduled_time)
            return user_reminders
            
        except Exception as e:
            logger.error(f"Error getting user reminders: {e}")
            return []
    
    async def cancel_reminder(self, reminder_id: str, user_id: str) -> bool:
        """Cancel a reminder"""
        try:
            if reminder_id in self.reminders:
                reminder = self.reminders[reminder_id]
                if reminder.user_id == user_id:
                    del self.reminders[reminder_id]
                    self._save_reminders()
                    logger.info(f"Cancelled reminder {reminder_id}")
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling reminder: {e}")
            return False
    
    def add_reminder_callback(self, callback):
        """Add a callback function to be called when reminders are due"""
        self.reminder_callbacks.append(callback)
    
    async def _reminder_checker(self):
        """Background task to check for due reminders"""
        while True:
            try:
                now = datetime.now()
                due_reminders = []
                
                for reminder in self.reminders.values():
                    if not reminder.is_sent and reminder.scheduled_time <= now:
                        due_reminders.append(reminder)
                
                # Process due reminders
                for reminder in due_reminders:
                    try:
                        # Mark as sent
                        reminder.is_sent = True
                        
                        # Call all registered callbacks
                        for callback in self.reminder_callbacks:
                            try:
                                await callback(reminder)
                            except Exception as e:
                                logger.error(f"Error in reminder callback: {e}")
                        
                        logger.info(f"Processed reminder {reminder.id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing reminder {reminder.id}: {e}")
                
                if due_reminders:
                    self._save_reminders()
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in reminder checker: {e}")
                await asyncio.sleep(60)  # Wait longer on error
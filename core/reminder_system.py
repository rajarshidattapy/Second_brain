"""
Reminder system for scheduling and managing user reminders with proper error handling
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import dateparser
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

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
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['scheduled_time'] = self.scheduled_time.isoformat()
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Reminder':
        data['scheduled_time'] = datetime.fromisoformat(data['scheduled_time'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)

class ReminderSystem:
    def __init__(self):
        self.reminders: Dict[str, Reminder] = {}
        self.reminder_callbacks: List[Callable] = []
        self._checker_task: Optional[asyncio.Task] = None
        self._reminders_file = Path(settings.DATA_DIR) / "reminders.json"
        
        # Load existing reminders
        self._load_reminders()
        
        # Start background task for checking reminders
        self._start_reminder_checker()
    
    def _load_reminders(self):
        """Load reminders from storage with error handling"""
        try:
            if self._reminders_file.exists():
                with open(self._reminders_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for reminder_data in data.get('reminders', []):
                        try:
                            reminder = Reminder.from_dict(reminder_data)
                            self.reminders[reminder.id] = reminder
                        except Exception as e:
                            logger.error(f"Failed to load reminder: {e}")
                            continue
                logger.info(f"Loaded {len(self.reminders)} reminders")
            else:
                logger.info("No existing reminders file found")
        except Exception as e:
            logger.error(f"Error loading reminders: {e}")
            # Continue with empty reminders dict
    
    def _save_reminders(self):
        """Save reminders to storage with error handling"""
        try:
            # Ensure directory exists
            self._reminders_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'reminders': [reminder.to_dict() for reminder in self.reminders.values()],
                'last_updated': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            # Write to temporary file first, then rename for atomic operation
            temp_file = self._reminders_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            temp_file.replace(self._reminders_file)
            logger.debug("Reminders saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving reminders: {e}")
    
    def parse_reminder_time(self, time_text: str) -> Optional[datetime]:
        """Parse natural language time into datetime with better error handling"""
        try:
            if not time_text or not time_text.strip():
                return None
            
            # Use dateparser to handle natural language
            parsed_time = dateparser.parse(
                time_text.strip(),
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'RETURN_AS_TIMEZONE_AWARE': False,
                    'DATE_ORDER': 'DMY'  # Day-Month-Year order
                }
            )
            
            if parsed_time:
                # If the parsed time is in the past, try to adjust it
                now = datetime.now()
                if parsed_time < now:
                    # If it's just a time (like "9am"), assume it's for today or tomorrow
                    if parsed_time.date() == now.date():
                        # If it's today but the time has passed, make it tomorrow
                        if parsed_time.time() < now.time():
                            parsed_time = parsed_time + timedelta(days=1)
                    else:
                        # For dates in the past, try adding a year
                        parsed_time = parsed_time.replace(year=now.year + 1)
                
                return parsed_time
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing time '{time_text}': {e}")
            return None
    
    async def create_reminder(self, user_id: str, content: str, time_text: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Create a new reminder with validation"""
        try:
            if not user_id or not user_id.strip():
                raise ValueError("User ID cannot be empty")
            
            if not content or not content.strip():
                raise ValueError("Reminder content cannot be empty")
            
            if not time_text or not time_text.strip():
                raise ValueError("Time specification cannot be empty")
            
            scheduled_time = self.parse_reminder_time(time_text)
            if not scheduled_time:
                logger.warning(f"Could not parse time: '{time_text}'")
                return None
            
            # Validate that the time is in the future
            if scheduled_time <= datetime.now():
                logger.warning(f"Scheduled time is in the past: {scheduled_time}")
                return None
            
            reminder_id = str(uuid.uuid4())
            reminder = Reminder(
                id=reminder_id,
                user_id=user_id.strip(),
                content=content.strip(),
                scheduled_time=scheduled_time,
                created_at=datetime.now(),
                metadata=metadata or {}
            )
            
            self.reminders[reminder_id] = reminder
            self._save_reminders()
            
            logger.info(f"Created reminder {reminder_id} for user {user_id} at {scheduled_time}")
            return reminder_id
            
        except Exception as e:
            logger.error(f"Error creating reminder: {e}")
            return None
    
    async def get_user_reminders(self, user_id: str, include_sent: bool = False) -> List[Reminder]:
        """Get all reminders for a user with validation"""
        try:
            if not user_id or not user_id.strip():
                raise ValueError("User ID cannot be empty")
            
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
        """Cancel a reminder with validation"""
        try:
            if not reminder_id or not reminder_id.strip():
                raise ValueError("Reminder ID cannot be empty")
            
            if not user_id or not user_id.strip():
                raise ValueError("User ID cannot be empty")
            
            if reminder_id in self.reminders:
                reminder = self.reminders[reminder_id]
                if reminder.user_id == user_id:
                    del self.reminders[reminder_id]
                    self._save_reminders()
                    logger.info(f"Cancelled reminder {reminder_id} for user {user_id}")
                    return True
                else:
                    logger.warning(f"User {user_id} attempted to cancel reminder {reminder_id} belonging to {reminder.user_id}")
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling reminder: {e}")
            return False
    
    def add_reminder_callback(self, callback: Callable):
        """Add a callback function to be called when reminders are due"""
        if callable(callback):
            self.reminder_callbacks.append(callback)
            logger.info("Added reminder callback")
        else:
            logger.error("Attempted to add non-callable reminder callback")
    
    def _start_reminder_checker(self):
        """Start the background reminder checker task"""
        if self._checker_task is None or self._checker_task.done():
            self._checker_task = asyncio.create_task(self._reminder_checker())
            logger.info("Started reminder checker task")
    
    async def _reminder_checker(self):
        """Background task to check for due reminders"""
        logger.info("Reminder checker started")
        
        while True:
            try:
                now = datetime.now()
                due_reminders = []
                
                # Find due reminders
                for reminder in self.reminders.values():
                    if not reminder.is_sent and reminder.scheduled_time <= now:
                        due_reminders.append(reminder)
                
                # Process due reminders
                for reminder in due_reminders:
                    try:
                        # Mark as sent first to prevent duplicate processing
                        reminder.is_sent = True
                        
                        # Call all registered callbacks
                        for callback in self.reminder_callbacks:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(reminder)
                                else:
                                    callback(reminder)
                            except Exception as e:
                                logger.error(f"Error in reminder callback: {e}")
                        
                        logger.info(f"Processed reminder {reminder.id} for user {reminder.user_id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing reminder {reminder.id}: {e}")
                        # Revert the sent status if processing failed
                        reminder.is_sent = False
                
                # Save changes if any reminders were processed
                if due_reminders:
                    self._save_reminders()
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                logger.info("Reminder checker task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in reminder checker: {e}")
                # Wait longer on error to prevent spam
                await asyncio.sleep(60)
    
    def stop(self):
        """Stop the reminder system"""
        if self._checker_task and not self._checker_task.done():
            self._checker_task.cancel()
            logger.info("Stopped reminder checker task")
"""
Sentiment and mood analysis for messages
"""
import re
from typing import Dict, List, Tuple
from datetime import datetime
from dataclasses import dataclass

@dataclass
class SentimentResult:
    sentiment: str  # positive, negative, neutral
    mood: str  # happy, sad, anxious, excited, reflective, etc.
    confidence: float
    emotions: List[str]
    intensity: float  # 0.0 to 1.0

class SentimentAnalyzer:
    def __init__(self):
        # Emotion keywords mapping
        self.emotion_keywords = {
            'happy': ['happy', 'joy', 'excited', 'great', 'awesome', 'wonderful', 'amazing', 'fantastic', 'love', 'smile', '😊', '😄', '😃', '🎉', '❤️'],
            'sad': ['sad', 'depressed', 'down', 'upset', 'crying', 'tears', 'hurt', 'pain', 'lonely', '😢', '😭', '💔', '😞'],
            'anxious': ['anxious', 'worried', 'stress', 'nervous', 'panic', 'fear', 'scared', 'overwhelmed', 'tension'],
            'angry': ['angry', 'mad', 'furious', 'rage', 'hate', 'annoyed', 'frustrated', 'irritated', '😡', '🤬'],
            'grateful': ['grateful', 'thankful', 'blessed', 'appreciate', 'thank you', 'thanks', '🙏'],
            'reflective': ['thinking', 'reflect', 'ponder', 'consider', 'wonder', 'contemplate', 'meditate'],
            'confused': ['confused', 'lost', 'unclear', 'puzzled', 'bewildered', 'perplexed', '🤔'],
            'tired': ['tired', 'exhausted', 'sleepy', 'drained', 'weary', 'fatigue', '😴'],
            'motivated': ['motivated', 'inspired', 'determined', 'focused', 'driven', 'ambitious', '💪'],
            'peaceful': ['calm', 'peaceful', 'serene', 'tranquil', 'relaxed', 'zen', 'mindful']
        }
        
        # Sentiment indicators
        self.positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'love', 'like', 'enjoy', 'happy', 'excited']
        self.negative_words = ['bad', 'terrible', 'awful', 'hate', 'dislike', 'sad', 'angry', 'frustrated', 'disappointed', 'upset']
        
        # Intensity modifiers
        self.intensity_modifiers = {
            'very': 1.5, 'extremely': 2.0, 'really': 1.3, 'so': 1.4, 'quite': 1.2,
            'somewhat': 0.8, 'a bit': 0.7, 'slightly': 0.6, 'kind of': 0.7
        }
    
    def analyze_sentiment(self, text: str) -> SentimentResult:
        """Analyze sentiment and mood of text"""
        text_lower = text.lower()
        
        # Clean text for analysis
        cleaned_text = re.sub(r'[^\w\s]', ' ', text_lower)
        words = cleaned_text.split()
        
        # Detect emotions
        detected_emotions = []
        emotion_scores = {}
        
        for emotion, keywords in self.emotion_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            if score > 0:
                emotion_scores[emotion] = score
                detected_emotions.append(emotion)
        
        # Calculate sentiment
        positive_score = sum(1 for word in words if word in self.positive_words)
        negative_score = sum(1 for word in words if word in self.negative_words)
        
        # Apply intensity modifiers
        intensity = 1.0
        for modifier, multiplier in self.intensity_modifiers.items():
            if modifier in text_lower:
                intensity *= multiplier
        
        # Determine overall sentiment
        if positive_score > negative_score:
            sentiment = 'positive'
            confidence = min(0.9, (positive_score - negative_score) / len(words) * 10)
        elif negative_score > positive_score:
            sentiment = 'negative'
            confidence = min(0.9, (negative_score - positive_score) / len(words) * 10)
        else:
            sentiment = 'neutral'
            confidence = 0.5
        
        # Determine primary mood
        if emotion_scores:
            primary_mood = max(emotion_scores.keys(), key=lambda k: emotion_scores[k])
        else:
            primary_mood = sentiment
        
        # Normalize intensity
        intensity = min(1.0, intensity)
        
        return SentimentResult(
            sentiment=sentiment,
            mood=primary_mood,
            confidence=confidence,
            emotions=detected_emotions,
            intensity=intensity
        )
    
    def analyze_mood_patterns(self, messages: List[Dict]) -> Dict:
        """Analyze mood patterns over time"""
        if not messages:
            return {}
        
        mood_counts = {}
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        daily_moods = {}
        
        for msg in messages:
            if 'sentiment_analysis' in msg:
                analysis = msg['sentiment_analysis']
                mood = analysis.get('mood', 'neutral')
                sentiment = analysis.get('sentiment', 'neutral')
                timestamp = msg.get('timestamp', '')
                
                # Count moods
                mood_counts[mood] = mood_counts.get(mood, 0) + 1
                sentiment_counts[sentiment] += 1
                
                # Group by day
                if timestamp:
                    try:
                        date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                        date_str = date.isoformat()
                        if date_str not in daily_moods:
                            daily_moods[date_str] = []
                        daily_moods[date_str].append(mood)
                    except:
                        pass
        
        # Calculate dominant mood
        dominant_mood = max(mood_counts.keys(), key=lambda k: mood_counts[k]) if mood_counts else 'neutral'
        
        # Calculate mood trend (last 7 days vs previous 7 days)
        recent_dates = sorted(daily_moods.keys())[-7:]
        previous_dates = sorted(daily_moods.keys())[-14:-7] if len(daily_moods) >= 14 else []
        
        trend = "stable"
        if recent_dates and previous_dates:
            recent_positive = sum(1 for date in recent_dates for mood in daily_moods[date] if mood in ['happy', 'grateful', 'motivated', 'peaceful'])
            previous_positive = sum(1 for date in previous_dates for mood in daily_moods[date] if mood in ['happy', 'grateful', 'motivated', 'peaceful'])
            
            if recent_positive > previous_positive * 1.2:
                trend = "improving"
            elif recent_positive < previous_positive * 0.8:
                trend = "declining"
        
        return {
            'mood_distribution': mood_counts,
            'sentiment_distribution': sentiment_counts,
            'dominant_mood': dominant_mood,
            'mood_trend': trend,
            'daily_patterns': daily_moods,
            'total_messages': len(messages)
        }
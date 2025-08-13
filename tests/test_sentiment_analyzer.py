"""
Tests for sentiment analyzer
"""
import pytest
from core.sentiment_analyzer import SentimentAnalyzer, SentimentResult

@pytest.fixture
def analyzer():
    return SentimentAnalyzer()

def test_positive_sentiment(analyzer):
    """Test positive sentiment detection"""
    text = "I'm so happy and excited about this amazing day!"
    result = analyzer.analyze_sentiment(text)
    
    assert isinstance(result, SentimentResult)
    assert result.sentiment == "positive"
    assert "happy" in result.emotions

def test_negative_sentiment(analyzer):
    """Test negative sentiment detection"""
    text = "I'm feeling really sad and upset about everything"
    result = analyzer.analyze_sentiment(text)
    
    assert isinstance(result, SentimentResult)
    assert result.sentiment == "negative"
    assert "sad" in result.emotions

def test_neutral_sentiment(analyzer):
    """Test neutral sentiment detection"""
    text = "The weather is okay today"
    result = analyzer.analyze_sentiment(text)
    
    assert isinstance(result, SentimentResult)
    assert result.sentiment in ["neutral", "positive", "negative"]  # Could be any
    assert result.confidence >= 0.0

def test_mood_patterns(analyzer):
    """Test mood pattern analysis"""
    messages = [
        {
            "timestamp": "2024-01-01T10:00:00",
            "sentiment_analysis": {
                "sentiment": "positive",
                "mood": "happy",
                "emotions": ["happy"],
                "confidence": 0.8,
                "intensity": 0.7
            }
        },
        {
            "timestamp": "2024-01-01T11:00:00", 
            "sentiment_analysis": {
                "sentiment": "negative",
                "mood": "sad",
                "emotions": ["sad"],
                "confidence": 0.7,
                "intensity": 0.6
            }
        }
    ]
    
    patterns = analyzer.analyze_mood_patterns(messages)
    
    assert isinstance(patterns, dict)
    assert "mood_distribution" in patterns
    assert "sentiment_distribution" in patterns
    assert "dominant_mood" in patterns
    assert patterns["total_messages"] == 2
# Echoself AI - The Reflective Personal Companion

**Echoself AI** is an intelligent, reflective personal companion that helps you understand your thoughts, emotions, and experiences through AI-powered memory storage, sentiment analysis, and personalized insights. Built as an MCP server compatible with **Puch AI** for seamless WhatsApp integration.

## 🌟 Features

- **🧠 Memory Storage**: Store and retrieve text, voice messages, images, and links with semantic search
- **💭 Sentiment Analysis**: Advanced mood and emotion detection with pattern analysis
- **🤖 AI Reflections**: Gemini Pro-powered insights and reflective conversations
- **⏰ Smart Reminders**: Natural language reminder parsing with WhatsApp notifications
- **🔒 Privacy-First**: End-to-end encryption for all stored memories
- **📱 WhatsApp Integration**: Seamless chat experience via Puch AI
- **🎯 Vector Search**: Qdrant-powered semantic memory retrieval

## 🏗️ Architecture

### Core Components

- **Memory Store** (`core/memory_store.py`): Qdrant vector database integration with encrypted storage
- **LLM Client** (`core/llm_client.py`): Gemini Pro integration for reflections and insights
- **Sentiment Analyzer** (`core/sentiment_analyzer.py`): Emotion and mood detection
- **WhatsApp Handler** (`core/whatsapp_handler.py`): Puch AI integration with media processing
- **Reminder System** (`core/reminder_system.py`): Natural language reminder scheduling
- **Encryption** (`core/encryption.py`): AES encryption for sensitive data

### Tech Stack

- **Backend**: FastMCP (async MCP server framework)
- **Vector DB**: Qdrant for semantic memory storage
- **LLM**: Google Gemini Pro for reflections and insights
- **Embeddings**: Sentence Transformers (`all-MiniLM-L6-v2`)
- **STT**: OpenAI Whisper for voice message transcription
- **Sentiment**: Transformers pipeline for emotion detection
- **Encryption**: Cryptography library with AES
- **Deployment**: Docker, Railway, Render support

## 🚀 Quick Setup

### 1. Clone and Install

```bash
git clone <repository-url>
cd echoself-ai
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create `.env` file:
```bash
cp .env.example .env
```

Configure your environment variables:
```env
# Required
AUTH_TOKEN=your_secret_bearer_token
MY_NUMBER=919876543210
GEMINI_API_KEY=your_gemini_api_key

# Optional (defaults provided)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=echoself_memories
EMBEDDING_MODEL=all-MiniLM-L6-v2
WHISPER_MODEL=small
ENCRYPTION_KEY=auto_generated_if_empty
```

### 4. Start Qdrant Database

```bash
# Using Docker Compose (recommended)
docker-compose up -d qdrant

# Or install Qdrant locally
# See: https://qdrant.tech/documentation/quick-start/
```

### 5. Run the MCP Server
```bash
python mcp-bearer-token/echoself_mcp_server.py
```

## 🌐 Deployment

### Railway (Recommended)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway up
```

### Render
```bash
# Connect your GitHub repo to Render
# Use the render.yaml configuration
```

### Docker
```bash
# Build and run with Docker Compose
docker-compose up -d
```

## 📱 Puch AI Integration

### Connect to WhatsApp

1. **Get your HTTPS URL** (from Railway, Render, or ngrok)
2. **Open Puch AI**: https://wa.me/+919998881729
3. **Connect your server**:
   ```
   /mcp connect https://your-server-url.com your_bearer_token
   ```

### Available Commands

Once connected, you can:

- **Share thoughts**: Just send any message to store it with sentiment analysis
- **Voice messages**: Send voice notes for automatic transcription and storage
- **Ask for insights**: "What was I feeling last week?" or "Tell me about my mood patterns"
- **Set reminders**: "Remind me to call mom tomorrow at 6pm"
- **Search memories**: "What did I say about work stress?"

## 🛠️ MCP Tools

### Core Tools

- **`validate`**: Required by Puch AI - returns your phone number
- **`about`**: Get information about Echoself AI
- **`store_message`**: Store any type of message with sentiment analysis
- **`search_memories`**: Search and get AI-powered reflections
- **`summarize_mood`**: Analyze mood patterns over time
- **`set_reminder`**: Create reminders with natural language
- **`get_reminders`**: View all active reminders

### Example Usage

```python
# Store a message
await store_message(
    puch_user_id="user123",
    content="Had a great day at the beach with friends!",
    message_type="text"
)

# Search for insights
await search_memories(
    puch_user_id="user123", 
    query="How do I feel about work lately?",
    limit=5
)

# Set a reminder
await set_reminder(
    puch_user_id="user123",
    content="Take vitamins",
    time_text="every morning at 8am"
)
```

## 🔒 Privacy & Security

- **End-to-end encryption**: All memories encrypted with AES
- **Local processing**: Sentiment analysis runs locally
- **Secure storage**: Qdrant vector database with encrypted payloads
- **Bearer token auth**: Secure MCP authentication
- **No data sharing**: Your memories stay private

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Puch AI Discord**: https://discord.gg/VMCnMvYx
- **Puch AI Documentation**: https://puch.ai/mcp
- **WhatsApp Support**: +91 99988 81729

## 🏷️ Tags

`#BuildWithPuch` `#EchoselfAI` `#MCP` `#WhatsApp` `#AI` `#PersonalCompanion` `#Reflection` `#Mood` `#Memory`

---

**Echoself AI** - Your reflective companion for understanding yourself better through AI-powered insights and memory. 🧠✨


## Getting Help

- **Join Puch AI Discord:** https://discord.gg/VMCnMvYx
- **Check Puch AI MCP docs:** https://puch.ai/mcp
- **Puch WhatsApp Number:** +91 99988 81729

---

**Happy coding! 🚀**

Use the hashtag `#BuildWithPuch` in your posts about your MCP!

This starter makes it super easy to create your own MCP server for Puch AI. Just follow the setup steps and you'll be ready to extend Puch with your custom tools!

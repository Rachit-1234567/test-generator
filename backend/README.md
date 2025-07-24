
# Automotive AI Assistant Backend

Python FastAPI backend for the Automotive AI Assistant, powered by Google Gemini AI.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your Google AI API key
```

3. Run the server:
```bash
python main.py
```

The server will start on http://localhost:8000

## API Endpoints

- `POST /api/chat` - Process chat messages with optional file attachments
- `GET /api/health` - Health check endpoint
- `GET /` - Root endpoint

## Environment Variables

- `GOOGLE_API_KEY` - Required: Your Google AI API key
- `GOOGLE_CLOUD_PROJECT` - Optional: Google Cloud project ID for Vertex AI
- `GOOGLE_CLOUD_LOCATION` - Optional: Google Cloud location (default: us-central1)

## File Upload Support

The backend supports uploading multiple files of any type to be processed by Gemini AI along with chat messages.

# 100x AI Tools Dashboard

A "Product Hunt" style AI Tools discovery platform. This project features a completely serverless FastAPI backend that dynamically retrieves and enriches AI tools using the latest **Google Gemini 1.5** AI models, alongside a React/Vite frontend for a staggeringly fast, responsive, and dynamic user experience.

## Features

- **Databaseless Serverless Architecture:** Fully optimized for cloud functions and Vercel environments. All application state is held Ephemerally in high-speed Python memory architectures, completely avoiding `read-only filesystem` constraints or sluggish SQLite lockouts.
- **Native AI Tool Discovery:** By default, live searches directly hook into Google Gemini API to instantly generate real, highly-relevant AI tool URLs, categories, and use cases.
- **Resilient Hybrid Fallback:** If the Gemini API hits a rate-limit or errors out, the backend seamlessly swaps to a proxy DuckDuckGo web-scraper without dropping the user request, ensuring the search never returns an ugly 500 error.
- **Community-Driven Pipeline:** Users can submit new AI Tools via URLs and instantly upvote tools they like. New submissions are instantly scraped and analyzed by AI to generate pristine descriptions.

## Tech Stack

- **Backend:** Python, FastAPI, DuckDuckGo Search (`ddgs`), Google GenAI SDK (`google-genai`).
- **Frontend:** React 19, Vite, Vanilla CSS.

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js & npm

### Backend Setup

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the development server:
   ```bash
   python main.py
   # The API will be available at http://localhost:8000
   # Swagger UI Docs: http://localhost:8000/docs
   ```

### Frontend Setup

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   # The UI will be available at the local Vite port (usually http://localhost:5173)
   ```

## Configuration & API Key

**IMPORTANT:** The project heavily relies on the Google Gemini API for fast, dynamic search discovery and content generation.

To configure the API key locally, create a `.env` file in the `backend/` directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

*Note: When deploying to Vercel, simply add `GEMINI_API_KEY` to your Project Environment Variables in the Vercel dashboard instead.*

## API Endpoints

- `GET /api/search?q={query}`: Live search for tools powered natively by Gemini + intelligent robust HTTP fallbacks.
- `POST /api/tools/submit`: Accepts a raw URL string, invisibly scrapes the `<title>` and `<meta>` tags of the website, queries Gemini to analyze the startup, and appends it to your live application state.
- `GET /api/tools`: Fetch the universally stored tools from memory.
- `POST /api/tools/{tool_id}/upvote`: Increment the upvote count instantly.

## License

This project is licensed under the MIT License.

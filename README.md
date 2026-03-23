# 100x AI Tools Dashboard

A "Product Hunt" style AI Tools discovery platform. This project features a FastAPI backend that scrapes and enriches AI tools using the Gemini API, alongside a React/Vite frontend for a fast, responsive, and dynamic user experience.

## Features

- **Live Search & Enrichment:** Search for AI tools using DuckDuckGo search, dynamically enriched with categories, pricing, and precise descriptions using the Google Gemini API.
- **Database-First Architecture:** Uses an SQLite database (`tools_v2.db`) for robust caching, faster performance, and persistent data storage.
- **Background Scraping:** Includes an admin API endpoint to trigger background jobs that scrape and discover new AI tools based on topics.
- **Community-Driven:** Users can upvote tools they like. Tools can be sorted by highest rated or newest.
- **Advanced Filtering:** Filter tools by category (Video, Image, Audio, Writing, Coding, Automation, Productivity, etc.) and pricing model (Free, Freemium, Paid).

## Tech Stack

- **Backend:** Python, FastAPI, SQLite, DuckDuckGo Search (`ddgs`), Google GenAI SDK.
- **Frontend:** React 19, Vite, Vanilla CSS.

## Project Structure

- `/backend/` - Contains the FastAPI application, database initialization, and logic for scraping and enriching AI tools.
- `/frontend/` - Contains the Vite-powered React UI.

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

**IMPORTANT:** The project uses the Google Gemini API for content enrichment (auto-categorization, pricing inference, and description generation).

To configure the API key, create a `.env` file in the `backend/` directory with the following content:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

The application uses `python-dotenv` to securely load the key during runtime.

## API Endpoints

- `GET /api/search?q={query}`: Live search for tools and auto-enrich them via LLM.
- `GET /api/tools`: Fetch stored tools with optional filters (`search`, `category`, `pricing`) and sorting (`sort=highest_rated`).
- `POST /api/tools/{tool_id}/upvote`: Increment the upvote count for a specific tool.
- `POST /api/admin/scrape?topic={topic}`: Start a background job to scrape and discover new AI tools for a given topic.

## License

This project is licensed under the MIT License.

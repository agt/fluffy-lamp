# Bulletin Board

A simple bulletin board where anyone can post notes and react with emojis.

## Stack
- **Frontend**: Vue 3 + Vite
- **Backend**: FastAPI + SQLite (via SQLAlchemy async)

## Development

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend (separate dev server with proxy)
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### Build frontend for production
```bash
cd frontend
npm run build   # outputs to backend/static/
```

## Run (production)
```bash
chmod +x start.sh
./start.sh     # http://localhost:8000
```

## Features
- Post notes with an optional author name
- 8 emoji reactions per note (👍 ❤️ 😂 😮 😢 👏 🔥 🎉)
- Delete notes
- Responsive masonry-style grid

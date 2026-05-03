# Web Interface Setup Guide

This guide explains how to set up and run the FastAPI backend and Next.js frontend.

## Backend Setup (FastAPI)

The backend orchestrates the AI agents and streams progress updates.

1. Navigate to the backend directory:
   cd backend

2. Create a virtual environment:
   python -m venv venv

3. Activate the virtual environment:
   # Windows
   .\venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate

4. Install dependencies:
   pip install -r requirements.txt

5. Start the backend server:
   python main.py

The API will be available at http://localhost:8001.

## Frontend Setup (Next.js)

The frontend provides the premium user interface.

1. Navigate to the frontend directory:
   cd frontend

2. Install dependencies:
   npm install

3. Start the development server:
   npm run dev

The web interface will be available at http://localhost:3000.

## Usage

1. Ensure the backend is running before starting the frontend.
2. Open http://localhost:3000 in your browser.
3. Enter your prompt and click Generate.
4. Monitor live progress through the phase cards and logs.

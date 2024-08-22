# PDF Chat App

This project consists of a Flask backend and a React frontend for chatting with PDFs using the Gemini API.

## Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd pdf-chat-app
   ```

2. Set up the virtual environment:
   ```
   python -m venv pdf_chat_env
   ```

3. Activate the virtual environment:
   - On Windows: `pdf_chat_env\Scripts\activate`
   - On macOS and Linux: `source pdf_chat_env/bin/activate`

4. Install backend dependencies:
   ```
   cd backend
   pip install -r requirements.txt
   cd ..
   ```

5. Install frontend dependencies:
   ```
   cd frontend
   npm install
   cd ..
   ```

## Running the Application

1. Make sure your virtual environment is activated.

2. Start the backend server:
   ```
   cd backend
   python app.py
   ```

3. In a new terminal, start the frontend development server:
   ```
   cd frontend
   npm start
   ```

4. Open your browser and navigate to `http://localhost:8080` to use the application.

5. When you're done, deactivate the virtual environment:
   ```
   deactivate
   ```

## Port Configuration

- Backend server runs on port 8000
- Frontend development server runs on port 8080

If you need to change these ports, update the following files:
- Backend: `backend/app.py`
- Frontend: `frontend/package.json` and API calls in React components
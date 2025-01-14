# Setup Instructions

## Prerequisites
Ensure that the following are installed on your system:
1. **Python** (version 3.8 or higher recommended)
2. **pip** (Python package installer)
3. **Virtualenv** (optional but recommended for isolating dependencies)

## Steps to Set Up the Project

### 1. Clone the Repository
```bash
git clone https://github.com/lenixbyte/django-chatapp.git
cd django-chatapp
```

### 2. Create a Virtual Environment 
```bash
python -m venv venv
source venv/bin/activate   # For Linux/Mac
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply Migrations
Set up the database by running the migrations:
```bash
python manage.py migrate
```

### 5. Run the Development Server
Start the Django development server:
```bash
python manage.py runserver
```
By default, the server will run on `http://127.0.0.1:8000`. 

## Project Features
1. **Signup and Login:** Users can register and log in.
2. **Chat Interface:** A collapsible menu displays all registered users. Logged-in users can initiate chats with others.
3. **Message History:** Chat messages are stored in the database and retrieved for display.
4. **WebSocket Support:** Real-time chat functionality enabled via WebSocket.
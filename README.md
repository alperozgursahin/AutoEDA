# AutoEDA: Intelligent Data Quality Analyzer 🚀

AutoEDA is a web-based platform designed to automate the early stages of data preparation for tabular datasets. Developed as a Senior Capstone Project (FENG 498) at Izmir University of Economics, it empowers data scientists and analysts to profile data, detect anomalies, and apply cleaning operations safely.

## 🌟 Core Philosophy
Unlike black-box automated tools, AutoEDA follows a strict **"Human-in-the-Loop"** approach. 
- **Explainability:** Every detected issue is paired with a clear, rule-based or LLM-supported cleaning recommendation.
- **Safety First:** The system never modifies the original dataset blindly. Users must explicitly approve or reject suggested actions before any transformation occurs.
- **Non-Destructive:** The original uploaded file is preserved; cleaning actions generate a versioned, safe output.

## 🛠️ Technology Stack
The project utilizes a modern, decoupled, and asynchronous architecture:
- **Backend:** FastAPI (Python) for high-performance, asynchronous API routing.
- **Data Engine:** Pandas, NumPy, and Scikit-learn for profiling and statistical analysis.
- **Task Queue:** Celery + Redis for asynchronous processing of heavy datasets without blocking the API.
- **Database:** PostgreSQL (Port: 5433) managed via SQLAlchemy ORM and Alembic migrations.
- **Frontend:** React (Next.js/Vite) for an interactive, state-managed user interface.

## ⚙️ Local Setup & Getting Started (For the Team)

Follow these steps to get the backend and database running on your local machine.

### 1. Prerequisites
- Python 3.11+
- Docker Desktop (must be running in the background)
- Git

### 2. Clone and Setup Environment
```bash
# Clone the repository
git clone [https://github.com/alperozgursahin/AutoEDA.git](https://github.com/alperozgursahin/AutoEDA.git)
cd AutoEDA

# Create and activate a virtual environment
python -m venv venv

# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install project dependencies
pip install -r requirements.txt
3. Spin up the Infrastructure
We use Docker to ensure everyone has the exact same database setup.

Bash
# Start PostgreSQL and Redis in the background
docker-compose up -d
Note: The database is exposed on port 5433 to prevent conflicts with existing local PostgreSQL installations.

4. Database Migrations
Create your local database tables using Alembic:

Bash
alembic upgrade head
5. Run the Application
Bash
uvicorn app.main:app --reload
The API will be available at http://127.0.0.1:8000. You can access the interactive Swagger documentation at http://127.0.0.1:8000/docs.

👥 Team

Alper Özgür Şahin 

İlayda Buzbuz 

Doğa Güneş 

Benhur Rahman Okur 

Supervisor: Asist. Prof. Dr. Kutluhan Erol

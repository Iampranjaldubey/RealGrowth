# 🌍 RealGrowth 2.0

> A premium, interactive Global Economic Data Dashboard for analyzing and comparing macroeconomic indicators across countries.

RealGrowth is a full-stack web application designed to visualize and analyze global economic data. It has been completely rebuilt (V2) to serve as a production-ready, resume-level project featuring a modern React frontend and a robust Python Flask backend.

---

## ✨ Features

- **Correlation Explorer**: Dynamically compute Pearson correlation and Linear Regression between any two economic indicators.
- **Global Debt Map**: Interactive 3D-style choropleth map for visualizing global Debt-to-GDP ratios.
- **Extensive Economic Metrics**:
  - GDP Per Capita (Top 10 Leaders & Historical Comparison)
  - Real Economic Growth Trends
  - Inflation Rates
  - Food Prices (Cost of a healthy diet)
  - Average Wages
  - Urban & Rural Population Distribution
- **Premium Design System**: Dark-mode-first aesthetic with glassmorphism, fluid animations, and customized Chart.js styling.
- **High Performance**: In-memory data caching on the backend, Gzip/Brotli payload compression, and Vite-optimized React frontend.

---

## 🛠️ Technology Stack

### Frontend
- **React.js 18** (Bootstrapped with Vite)
- **React Router** for SPA navigation
- **Chart.js & React-Chartjs-2** for interactive line, bar, and pie charts
- **React Simple Maps & D3-Geo** for choropleth data visualization
- **Custom CSS** for a dependency-free, highly customized glassmorphic UI

### Backend
- **Python 3.11 & Flask** (Blueprint Architecture)
- **Pandas & NumPy** for data ingestion, cleaning, and statistical analysis
- **Production Extensions**:
  - `Flask-Talisman` (Security Headers)
  - `Flask-Limiter` (Rate Limiting)
  - `Flask-Compress` (Payload Compression)
  - `Gunicorn` (WSGI HTTP Server)

### Infrastructure
- **Docker & Docker Compose** for seamless containerized deployment
- **Nginx** for serving static frontend assets

---

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose (Recommended)
- Python 3.11+ and Node.js 18+ (For local native development)

### 🐳 Run with Docker (Production Ready)

The easiest way to spin up the entire application:

```bash
# Clone the repository
git clone https://github.com/Iampranjaldubey/RealGrowth.git
cd RealGrowth

# Build and start the containers
docker-compose up --build
```
- The frontend will be available at `http://localhost:3000`
- The backend API will be available at `http://localhost:5000`

### 💻 Run Natively (Local Development)

#### 1. Setup Backend
```bash
cd backend
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt

# Start Flask server
python app.py
```

#### 2. Setup Frontend
Open a new terminal:
```bash
cd frontend
npm install
npm run dev
```

---

## 📁 Project Structure

```
RealGrowth/
├── backend/                  # Flask REST API
│   ├── api/                  # Blueprint route controllers
│   ├── data/                 # Raw CSV datasets
│   ├── services/             # Centralized Data Loader & caching
│   ├── utils/                # Validation helpers
│   ├── tests/                # Pytest suite
│   ├── app.py                # App Factory & config
│   └── requirements.txt      
├── frontend/                 # React SPA
│   ├── src/                  
│   │   ├── components/       # Reusable UI/Chart components
│   │   ├── context/          # React Context (Theme)
│   │   ├── hooks/            # Custom API caching hooks
│   │   ├── pages/            # View routing
│   │   └── utils/            # Formatters & Chart Config
│   ├── vite.config.js        # Vite bundler config
│   └── package.json          
└── docker-compose.yml        # Orchestration
```

---

## 📄 License
This project is open-source and available under the MIT License.

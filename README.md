# 🐱 Cat Food Advisor - ReAct AI Agent

An autonomous AI Agent designed to evaluate cat food quality based on professional veterinary standards (FEDIAF) and real-time web data.

## 🚀 Overview
Unlike standard chatbots, this advisor is a **ReAct Agent** that:
1.  **Searches** the web for real-time nutritional compositions of specific cat foods.
2.  **Calculates** precise Dry Matter (DM) values and Carbohydrate (NFE) content using a custom Python tool.
3.  **Analyzes** the results against the specific health profile of the cat (age, breed, health issues).
4.  **Verdicts** the food as GOOD, ACCEPTABLE, or AVOID in the user's native language.

## 🛠️ Technology Stack
- **AI Engine:** Groq (Llama 3.3 70B Versatile)
- **Framework:** FastAPI (Backend)
- **Search Tool:** DuckDuckGo Search API
- **Language:** Python 3.9+
- **Deployment:** Hugging Face Spaces (Docker)

## 🏗️ Project Structure
- `backend/app.py`: The core Agent engine with ReAct loop and Tool definitions.
- `client/cat_food_advisor.py`: A lightweight client to interact with the API.
- `Dockerfile`: Configuration for containerized deployment.

## ⚙️ Features
- **Auto-Detection:** Detects user language automatically based on input.
- **Metric System:** Operates strictly on European units (grams, kg, mg/kg).
- **Nutritional Safety:** Checks for Taurine levels and Calcium-to-Phosphorus (Ca:P) ratios.
- **Hallucination Protection:** Offloads all mathematical calculations to specialized Python functions.
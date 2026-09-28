# Plutus

This is my submission for Software Engineering & DevOps (VH6033).

Developed off of previous work, which was done on my private repo. I have imported here to allow access for graders.

## Render Deployment

The application is deployed using Render.

Deployment URL: https://plutus-igvb.onrender.com/

## Requirements

- Python 3
- PostgreSQL

## Installation

1. Create a virtual environment:

    python -m venv venv

2. Activate the virtual environment:

    venv\Scripts\activate

3. Install the dependencies:

    pip install -r requirements.txt

4. Create a `.env` file containing:

    SECRET_KEY=your-secret-key
    
    DATABASE_URL=postgresql://username:password@localhost/database_name

## Running the Application

    python -m flask --app wsgi run

## Adding Sample Data

    python seed.py

## Running the Tests

    pip install pytest
    pytest

# Use a slim Python image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy all local files into the container
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expose port the Flask app will run on
EXPOSE 8000

# Default command to run the app with Gunicorn
CMD ["gunicorn", "flask_app:app", "--bind", "0.0.0.0:8000"]

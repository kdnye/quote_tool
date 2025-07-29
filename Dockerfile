# Use a slim Python image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy all local files into the container
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expose port Streamlit will run on
EXPOSE 8501

# Default command to run the app
CMD ["streamlit", "run", "app.py", "--server.enableCORS=false"]

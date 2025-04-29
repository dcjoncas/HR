# Use a Python base image
FROM python:3.9-slim

# Install Poppler and dependencies (required for pdf2image)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app

# Copy application files to the container
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expose the port that Render expects (Render uses port 10000 by default)
EXPOSE 10000

# Run the Flask app
CMD ["python", "app1.py"]
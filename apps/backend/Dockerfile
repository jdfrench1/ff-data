FROM python:3.9-slim as scraper

# Set working directory
WORKDIR /app

# Copy requirement files and install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the scraper script into the container
COPY ffscraper.py /app/ffscraper.py

# Command to run the scraper
CMD ["python", "ffscraper.py"]

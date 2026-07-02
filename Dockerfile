# Use an official lightweight Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the specified Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your local application code into the container
COPY . .

# Expose the standard Streamlit port
EXPOSE 8501

# Configure Streamlit to run smoothly inside an isolated network environment
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
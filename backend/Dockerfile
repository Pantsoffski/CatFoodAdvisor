FROM python:3.9

# Ensure Python logs are sent straight to terminal
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user for Hugging Face Spaces security
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy the rest of the application files to the user's app directory
# Fixed the split line issue from previous version
COPY --chown=user . $HOME/app

# Hugging Face Spaces requires port 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
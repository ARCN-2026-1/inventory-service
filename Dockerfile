FROM python:3.11-slim

# Install uv for fast dependency resolution and installation
RUN pip install uv

# Set the working directory
WORKDIR /app

# Copy dependency files first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into a local .venv (uv sync handles this)
RUN uv sync --frozen --no-install-project --no-dev

# Copy application source code
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev

# Expose the API port
EXPOSE 8000

# Command to run the FastAPI server by default
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM mcr.microsoft.com/devcontainers/python:3.11

# Install Node.js 20 (required by Angular 20 dashboard)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install dependencies from requirements.txt
COPY requirements.txt /tmp/pip-tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp

# Set default workspace
WORKDIR /workspace

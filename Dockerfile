# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080
ENV DISPLAY=:99

# Install system dependencies required for Firefox/Camoufox
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    unzip \
    curl \
    xvfb \
    xauth \
    ca-certificates \
    fonts-liberation \
    fonts-freefont-ttf \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    gpg \
    # Firefox/Camoufox specific dependencies
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcb-dri3-0 \
    libxcb-shm0 \
    libxss1 \
    libxtst6 \
    libpangocairo-1.0-0 \
    libcairo-gobject2 \
    libgdk-pixbuf-xlib-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN useradd -m -u 1000 appuser

# Set the working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Switch to appuser and install Python packages in user directory
USER appuser
RUN pip install --user --no-cache-dir -r requirements.txt

# Add user's local bin to PATH
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Install Camoufox browser as user
RUN python3 -m camoufox fetch

# Pre-download and cache by running a simple test
RUN python3 -c "import camoufox; print('Camoufox import successful')"

# Switch back to root to copy files
USER root

# Copy application files
COPY . .

# Set proper ownership and permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user for runtime
USER appuser

# Expose the port
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]
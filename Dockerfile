FROM python:3-slim

# Set the working directory
WORKDIR /app

# Ensure matplotlib uses a headless backend inside Docker
ENV MPLBACKEND=Agg
# Default export.xml location when mounted as a volume
ENV EXPORT_XML=/export.xml
# Default output directory for generated files
ENV OUTPUT_DIR=/out

# Create the default output directory
RUN mkdir -p /out

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY src/ .

# Command to run the application
CMD ["python", "applehealth.py"]

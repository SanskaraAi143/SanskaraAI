# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY ./requirements.txt /app/sanskara/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r /app/sanskara/requirements.txt

# Copy the rest of the application code
COPY ./ /app/sanskara/

# Expose the port that FastAPI runs on
EXPOSE 8765

# Command to run the FastAPI application
# CMD ["uvicorn", "sanskara.main:app", "--host", "0.0.0.0", "--port", "8765", "--reload", "--log-level", "debug"]
CMD ["python", "app/sanskara/main.py"]
FROM python:3.8-slim

# Set the working directory
WORKDIR /src

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the entire project
COPY . .

# Set environment variables
ENV FLASK_APP=app/routes.py
ENV FLASK_RUN_HOST=0.0.0.0

# Command to run the application
CMD ["flask", "run"]

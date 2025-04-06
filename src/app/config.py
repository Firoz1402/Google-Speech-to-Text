import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GCP_API_KEY = os.getenv('GCP_API_KEY')

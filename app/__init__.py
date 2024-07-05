# Initializes Flask app and brings together other components.
from flask import Flask

app = Flask(__name__)

from app import routes

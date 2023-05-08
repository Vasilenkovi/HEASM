
import sys
import logging

sys.path.insert(0, '/var/www/Web')
sys.path.insert(0, '/var/www/Web/venv/Lib/site-packages/')

# Set up logging
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

# Import and run the Flask app
from webApp import app as application


from flask import Blueprint
from . import views

monitor_bp = Blueprint('monitor', __name__, template_folder='../../templates')

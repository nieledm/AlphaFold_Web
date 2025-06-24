from flask import Blueprint
from . import views

logs_bp = Blueprint('logs', __name__, template_folder='../../templates')

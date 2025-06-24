from flask import Blueprint
from . import views

aut_bp = Blueprint('aut', __name__, template_folder='../../templates')
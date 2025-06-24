from flask import Blueprint
from . import views

users_bp = Blueprint('users', __name__, template_folder='templates')
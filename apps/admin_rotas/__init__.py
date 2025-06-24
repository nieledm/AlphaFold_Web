from flask import Blueprint
from . import views

admins_bp = Blueprint('admins', __name__, template_folder='templates')
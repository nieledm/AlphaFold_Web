from flask import Blueprint
from . import views

apf_bp = Blueprint('apf', __name__, template_folder='../../templates')
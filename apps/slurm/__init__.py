from flask import Blueprint

slurm_bp = Blueprint('slurm', __name__)

from .routes import *
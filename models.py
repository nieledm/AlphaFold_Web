from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime


db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # sqlite: INTEGER DEFAULT 0  -> Boolean no Python, mapeia 0/1
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False)

    # relationship
    uploads = db.relationship("Upload", backref="user", lazy=True)
    logs = db.relationship("Log", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.id} {self.email}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
        }

class Upload(db.Model):
    __tablename__ = "uploads"

    id = db.Column(db.Integer, primary_key=True)

    # Foreign key
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    file_name = db.Column(db.String(255), nullable=False)
    base_name = db.Column(db.String(255), nullable=False)

    status = db.Column(db.String(50), nullable=False, default="PENDENTE")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    priority = db.Column(db.Integer, default=0)

    details = db.Column(db.Text)

    def __repr__(self):
        return f"<Upload {self.id} {self.base_name} Status={self.status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "file_name": self.file_name,
            "base_name": self.base_name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "priority": self.priority,
            "details": self.details,
        }

class Config(db.Model):
    __tablename__ = "config"

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text)

    def __repr__(self):
        return f"<Config {self.key}={self.value}>"

    def to_dict(self):
        return {
            "key": self.key,
            "value": self.value,
        }

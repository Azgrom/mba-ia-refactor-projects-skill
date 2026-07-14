from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from timeutil import utcnow


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def set_password(self, pwd):
        # Adaptive, salted hash (F-004). Existing MD5 digests cannot be migrated
        # and will simply fail check_password_hash, forcing a password reset.
        self.password = generate_password_hash(pwd)

    def check_password(self, pwd):
        try:
            return check_password_hash(self.password, pwd)
        except (ValueError, TypeError):
            # Legacy MD5 digests are not a recognized hash format.
            return False

    def is_admin(self):
        return self.role == 'admin'

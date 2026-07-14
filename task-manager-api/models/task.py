from database import db
from timeutil import ensure_utc, utcnow

TERMINAL_STATUSES = ('done', 'cancelled')


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='pending')
    priority = db.Column(db.Integer, default=3)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    due_date = db.Column(db.DateTime(timezone=True), nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref='tasks')
    category = db.relationship('Category', backref='tasks')

    def is_overdue(self, now=None):
        """The single owner of the overdue rule (F-011).

        Previously inlined at six route sites while this method went uncalled.
        """
        if not self.due_date:
            return False
        if self.status in TERMINAL_STATUSES:
            return False
        return ensure_utc(self.due_date) < (now or utcnow())

    def tag_list(self):
        return self.tags.split(',') if self.tags else []

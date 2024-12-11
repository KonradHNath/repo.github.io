from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=True)
    google_id = db.Column(db.String(200), unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    birth_date = db.Column(db.Date, nullable=True)  # Fødselsdato

    # Define the relationship with Meeting
    meetings = db.relationship('Meeting', secondary='meeting_participants', back_populates='participants')

class Meeting(db.Model):
    __tablename__ = 'meeting'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    max_participants = db.Column(db.Integer, nullable=True)
    
    # Relationship to participants (Users)
    participants = db.relationship('User', secondary='meeting_participants', back_populates='meetings')

class MeetingParticipants(db.Model):
    __tablename__ = 'meeting_participants'
    meeting_id = db.Column(db.Integer, db.ForeignKey('meeting.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)

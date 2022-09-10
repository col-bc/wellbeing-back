from datetime import datetime, timedelta
import json
from typing import List

from bcrypt import checkpw, gensalt, hashpw
from flask import current_app
from jwt import encode, decode

from .app import db


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    check_ins = db.relationship('CheckIn', backref='user', lazy=True)
    journal = db.relationship('Journal', backref='user', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    updated_at = db.Column(db.DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow())
    
    def __init__(self, name:str, email:str, password_hash:str, dob:datetime):
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.dob = dob
    
    def __repr__(self):
        return f'<User {self.name}>'
    
    def serialize(self) -> dict:
        '''Serialize the user to a dict'''
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'dob': self.dob,
            'check_ins': [ci.serialize() for ci in self.check_ins],
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
       
    @staticmethod
    def hash_password(plain_password:str) -> str:
        '''Return a hashed password from plain password using bcrypt'''
        return hashpw(plain_password.encode('utf-8'), gensalt()).decode('utf-8')
        
    def check_password(self, plain_password:str) -> bool:
        '''Check if plain_password is the same as the hashed password'''
        return checkpw(plain_password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def generate_auth_token(self) -> str:
        '''Generate an jwt auth token for the user'''
        payload = {
            'sub': self.id,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(days=1)
        }
        return encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
        
    @staticmethod
    def check_auth_token(token:str) -> 'User':
        '''Check if the token is valid'''
        try:
            payload = decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            return payload['sub']
        except Exception as e:
            print(e)
            return None
    
            
class CheckIn(db.Model):
    __tablename__ = 'check_in'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow())
    rating = db.Column(db.Integer, nullable=False)
    symptoms = db.Column(db.Text, nullable=True, default='[]')
    activities = db.Column(db.Text, nullable=True, default='[]')
    notes = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    
    def __init__(self, rating:int, date:datetime, user_id:int, symptoms:list=[], notes:str=None, activities:list=[]):
        self.rating = rating
        self.user_id = user_id
        self.symptoms = symptoms
        self.date = date
        self.notes = notes
        self.activities = activities
        
    def __repr__(self):
        return f'<CheckIn {self.id}>'
    
    def serialize(self) -> dict:
        '''Serialize the CheckIn to a dict'''
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'rating': self.rating,
            'symptoms': json.dumps(self.symptoms),
            'activities': json.dumps(self.activities),
            'notes': self.notes,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
        }
        
    def update(self, new_data):
        '''Update the CheckIn with new data'''
        self.rating = new_data.get('rating', self.rating)
        self.date = new_data.get('date', self.date)
        self.activities = new_data.get('activities', self.activities)
        self.symptoms = new_data.get('symptoms', self.symptoms)
        self.notes = new_data.get('notes', self.notes)
        db.session.commit()
        
    def get_symptoms(self) -> List[str]:
        '''Get the `symptoms` as a list'''
        return json.loads(self.symptoms)
    
    def get_activities(self) -> List[str]:
        '''Get the `activities` as a list'''
        return json.loads(self.activities)
    
    @staticmethod
    def get_rating_totals(user_id:int) -> dict:
        '''Calculate totals number of ratings for each rating level for a user'''
        return {
            'very_bad': CheckIn.query.filter_by(user_id=user_id, rating=1).count(),
            'bad': CheckIn.query.filter_by(user_id=user_id, rating=2).count(),
            'neutral': CheckIn.query.filter_by(user_id=user_id, rating=3).count(),
            'good': CheckIn.query.filter_by(user_id=user_id, rating=4).count(),
            'very_good': CheckIn.query.filter_by(user_id=user_id, rating=5).count(),
        }
       
    
class JournalPage(db.Model):
    __tablename__ = 'journal_page'
    id = db.Column(db.Integer, primary_key=True)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow())
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow())
    updated_at = db.Column(db.DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow())

    def __init__(self, journal_id:int, body:str, date:datetime=datetime.now()):
        self.journal_id = journal_id
        self.date = date
        self.body = body
        
    def __repr__(self):
        return f'<JournalPage {self.id}>'
    
    def serialize(self) -> dict:
        return { 
            'id': self.id,
            'journal_id': self.journal_id,
            'date': self.date.isoformat(),
            'body': self.body,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
       
    def update(self, new_data):
        self.body = new_data.get('body', self.body)
        self.updated_at = datetime.utcnow()
        
    @staticmethod
    def get_page(journal_id:int, date:datetime) -> 'JournalPage':
        '''Get the journal page for a given date'''
        return JournalPage.query.filter_by(journal_id=journal_id, date=date).first()
    
    @staticmethod
    def search_pages(journal_id:int, query:str) -> List['JournalPage']:
        '''Search for journal pages'''
        return JournalPage.query.filter_by(journal_id=journal_id).filter(JournalPage.body.like(f'%{query}%')).all()
    
       
class Journal(db.Model):
    __tablename__ = 'journal'
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pages = db.relationship('JournalPage', backref='journal', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow())

    def __init__(self, owner_id:int):
        self.owner_id = owner_id
        
    def __repr__(self):
        return f'<Journal {self.id}>'
    
    def serialize(self) -> dict:
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'pages': [page.serialize() for page in self.pages],
            'created_at': self.created_at.isoformat(),
        }
        
    def get_pages(self) -> List[JournalPage]:
        '''Get the journal pages for the user's journal'''
        return self.pages
    
    def add_page(self, body:str, date:datetime=datetime.now()):
        '''Add a journal page to the journal'''
        page = JournalPage(self.id, body, date)
        db.session.add(page)
        db.session.commit()
        return page
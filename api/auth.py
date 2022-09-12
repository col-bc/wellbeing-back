from datetime import datetime
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request
from flask_cors import CORS

from ..app import db
from ..models import User

auth_api = Blueprint('auth_api', __name__, url_prefix='/api/auth')
CORS(auth_api)

""" 
Endpoints
---------
`/api/auth/login`
    -> POST { `email`, `password` }
        <- 201 { `success` }
        <- 400 { `error` }
`/api/auth/register`
    -> POST { `name`, `email`, `dob`, `password` }
        <- 200 { `user` }
"""

def login_required(func):
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not request.headers.get('Authorization'):
            return jsonify({'error': 'Authorization header is required'}), 401
        
        auth_header = request.headers.get('Authorization')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        user_id = User.check_auth_token(token)
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        g.user = User.query.get(user_id)
        
        return func(*args, **kwargs)

    return wrapper


@auth_api.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if (
        not data 
        or not data.get('email')
        or not data.get('password')
        or not data.get('name') 
        or not data.get('dob')
    ):
        return jsonify({'error': 'Invalid payload'}), 400
    
    # check if user already exists
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'error': 'User already exists'}), 400
    
    user: User = User(
        name=data.get('name'),
        email=data.get('email'),
        dob=datetime.strptime(data.get('dob'), '%Y-%m-%d'),
        password_hash=User.hash_password(data.get('password'))
    )
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'success': 'User registered'}), 201
    

@auth_api.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if (
        not data
        or not data.get('email')
        or not data.get('password')
    ):
        return jsonify({'error': 'Invalid payload'}), 400
    
    user: User = User.query.filter_by(email=data.get('email')).first()
    if not user:
        return jsonify({'error': 'Invalid username or password'}), 400
    if not user.check_password(data.get('password')):
        return jsonify({'error': 'Invalid username or password'}), 400
    
    token = user.generate_auth_token()
    return jsonify({'token': token}), 200    


@auth_api.route('/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    if not data.get('current_password') or not data.get('new_password'):
        return jsonify({'error': 'Invalid payload'}), 400

    user: User = g.user
    if not user.check_password(data.get('current_password')):
        return jsonify({'error': 'Invalid username or password'}), 400
    
    user.password_hash = User.hash_password(data.get('new_password'))
    db.session.commit()
    
    return jsonify({'success': 'Password changed'}), 200

from datetime import datetime
from flask import Blueprint, g, jsonify, request
from flask_cors import CORS

from ..app import db
from ..models import CheckIn, Journal, JournalPage
from .auth import login_required

user_api = Blueprint('user_api', __name__, url_prefix='/api/user')
CORS(user_api)


"""
Endpoints
---------
/api/user/
Auth Scheme: Bearer JWT
    -> GET 
        <- 200 { user }
        <- 401 { error }
    -> PUT { name, dob, password }
        <- 200 { user }
        <- 400 { error }
        <- 401 { error }
    -> DELETE { password }
        <- 200 { success }
        <- 400 { error }
        <- 401 { error }
/api/user/check-in
Auth Scheme: Bearer JWT
    -> GET
        <- 200 { check_ins, total }
        <- 401 { error }
    -> POST { rating, date, activities?, symptoms?, notes? }
        <- 200 { check_in }
        <- 400 { error }
        <- 401 { error }
/api/user/check-in/<check_in_id>
Auth Scheme: Bearer JWT
    -> GET
        <- 200 { check_in }
        <- 400 { error }
        <- 404 { error }
        <- 401 { error }
"""

@user_api.route('/', methods=['GET'])
@login_required
def get_current_user():
    ''' Get current user '''
    return jsonify(g.user.serialize())


@user_api.route('/', methods=['PUT'])
@login_required
def update_user():
    ''' Update user details for token owner '''
    data = request.get_json()
    if not data or not data.get('name') or not data.get('email'):
        return jsonify({'error': 'Invalid payload'}), 400
    
    g.user.name = data.get('name')
    g.user.email = data.get('email')
    db.session.commit()

    return jsonify(g.user.serialize())


@user_api.route('/', methods=['DELETE'])
@login_required
def delete_user():
    ''' Delete the token owner '''
    data = request.get_json()
    if not data or not data.get('password'):
        return jsonify({'error': 'Invalid payload'}), 400
    if not g.user.check_password(data.get('password')):
        return jsonify({'error': 'Invalid password'}), 400
    
    db.session.delete(g.user)
    db.session.commit()
    
    return jsonify({'success': 'User deleted'}), 200


''' Check-in endpoints '''


@user_api.route('/check-in', methods=['GET'])
@login_required
def get_check_ins():
    ''' Get all check-ins for token owner '''
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    check_ins = CheckIn.query.filter_by(user_id=g.user.id).order_by(CheckIn.date.desc()).paginate(page, limit, False)   

    return jsonify({
        'check_ins': [check_in.serialize() for check_in in check_ins.items],
        'totals': CheckIn.get_rating_totals(g.user.id),
        'pages': check_ins.pages,
        'page': check_ins.page,
        'has_next': check_ins.has_next,
    })


@user_api.route('/check-in', methods=['POST'])
@login_required
def create_check_in():
    ''' Create a new check-in for the token owner '''
    data = request.get_json()
    if (
        not data or 
        not data.get('date') or
        not data.get('rating')
    ):
        return jsonify({'error': 'Invalid payload'}), 400
    
    ci = CheckIn(
        rating=data.get('rating'),
        notes=data.get('notes'),
        date=datetime.strptime(data.get('date'), '%Y-%m-%dT%H:%M'),
        activities=data.get('activities'),
        symptoms=data.get('symptoms'),
        user_id = g.user.id
    )
    db.session.add(ci)
    db.session.commit()
    return jsonify(ci.serialize()), 201


@user_api.route('/check-in/<int:check_in_id>', methods=['GET'])
@login_required
def get_check_in_by_id(check_in_id):
    ''' Get a check-in by id '''
    ci = CheckIn.query.filter_by(id=check_in_id).first()
    if not ci:
        return jsonify({'error': 'Check-in not found'}), 404
    return jsonify(ci.serialize())


@user_api.route('/check-in/<int:check_in_id>', methods=['PUT'])
@login_required
def update_check_in_by_id(check_in_id):
    ''' Update a check-in by id '''
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid payload'}), 400
    
    ci = CheckIn.query.filter_by(id=check_in_id).first()
    if not ci:
        return jsonify({'error': 'Check-in not found'}), 404
    
    ci.update(data)
    
    return jsonify(ci.serialize())


@user_api.route('/check-in/<int:check_in_id>', methods=['DELETE'])
@login_required
def delete_check_in_by_id(check_in_id):
    ''' Delete a check-in by id '''
    ci = CheckIn.query.filter_by(id=check_in_id).first()
    if not ci:
        return jsonify({'error': 'Check-in not found'}), 404
    db.session.delete(ci)
    db.session.commit()
    return jsonify({'success': 'Check-in deleted'}), 200


''' Journal endpoints '''


@user_api.route('/journal', methods=['GET'])
@login_required
def get_journal():
    ''' Get all journal entries for token owner '''
    if not g.user.journal:
        # Create a new journal if one doesn't exist
        journal = Journal(owner_id=g.user.id)
        db.session.add(journal)
        db.session.commit()
        return jsonify(g.user.journal[0].serialize()), 201
    
    return jsonify(g.user.journal[0].serialize()), 200


@user_api.route('/journal', methods=['POST'])
@login_required
def create_journal_page():
    ''' Create a new page in the token bearer's journal '''
    data = request.get_json()
    if (
        not data
        or not data.get('date')
        or not data.get('body')
    ):
        return jsonify({'error': 'Invalid payload'}), 400
    
    page = g.user.journal[0].add_page(
        data.get('body'),
        datetime.strptime(data.get('date'), '%Y-%m-%dT%H:%M')
    )
    
    return jsonify(page.serialize()), 201


@user_api.route('/journal/<int:page_id>', methods=['PUT'])
@login_required
def update_journal_page(page_id: int):
    ''' Update a journal page by id '''
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid payload'}), 400
    
    page = JournalPage.query.filter_by(id=page_id).first()
    if not page:
        return jsonify({'error': 'Page not found'}), 404
    
    page.update(data)
    
    return jsonify(page.serialize())


@user_api.route('/journal/<int:page_id>', methods=['DELETE'])
@login_required
def delete_journal_pate(page_id: int):
    ''' Delete a journal page by id '''
    page = JournalPage.query.filter_by(id=page_id).first()
    if not page:
        return jsonify({'error': 'Page not found'}), 404
    
    db.session.delete(page)
    db.session.commit()
    
    return jsonify({'success': 'Page deleted'}), 200
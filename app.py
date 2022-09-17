from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate =  Migrate()

def create_app():
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY='dev',
        DEBUG=1,
        SQLALCHEMY_DATABASE_URI='mysql+pymysql://remote:CBC00p3r!@192.168.1.74/wellbeing',
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )
    
    with app.app_context():
        db.init_app(app)
        migrate.init_app(app, db)
        db.create_all(app=app)
        print(' * Database connected')
    
    from .api.auth import auth_api
    from .api.user import user_api
    app.register_blueprint(auth_api)
    app.register_blueprint(user_api)
    
    @app.before_request
    def handle_preflight():
        if request.method == 'OPTIONS':
            return jsonify({}), 204
        
    return app
    
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)

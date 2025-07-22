import os
import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify, redirect, abort, render_template
from flask_sqlalchemy import SQLAlchemy
from utils import generate_short_code
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///default.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
class URLMap(db.Model):
    __tablename__ = 'urls'
    id = db.Column(db.Integer, primary_key=True)
    long_url = db.Column(db.String(2048), nullable=False)
    short_code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    clicks = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<URLMap {self.short_code} -> {self.long_url[:30]}>"
@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    data = request.get_json()
    if not data or 'long_url' not in data:
        return jsonify({'error': 'The "long_url" field is required.'}), 400

    long_url = data.get('long_url')
    custom_alias = data.get('custom_alias')
    short_code = None

    if custom_alias:
        if ' ' in custom_alias:
            return jsonify({'error': 'Custom alias cannot contain spaces.'}), 400
        if not custom_alias.isalnum():
            return jsonify({'error': 'Custom alias can only contain letters and numbers.'}), 400
        if not (4 <= len(custom_alias) <= 30):
            return jsonify({'error': 'Custom alias must be between 4 and 30 characters long.'}), 400

        existing_alias = URLMap.query.filter_by(short_code=custom_alias).first()
        if existing_alias:
            return jsonify({'error': 'This custom alias is already in use. Please choose another.'}), 409
        short_code = custom_alias
    else:
        while True:
            generated_code = generate_short_code()
            existing_code = URLMap.query.filter_by(short_code=generated_code).first()
            if not existing_code:
                short_code = generated_code
                break

    new_url = URLMap(long_url=long_url, short_code=short_code)
    db.session.add(new_url)
    db.session.commit()
    short_url = f"{request.host_url}{short_code}"
    return jsonify({'short_url': short_url}), 201
@app.route('/<string:short_code>')
def redirect_to_long_url(short_code):
    url_map_entry = URLMap.query.filter_by(short_code=short_code).first()
    if url_map_entry:
        url_map_entry.clicks += 1
        db.session.commit()  # ✅ fixed typo here
        return redirect(url_map_entry.long_url)
    else:
        abort(404)
@app.route('/analytics/<string:short_code>')
def show_analytics(short_code):
    url_map_entry = URLMap.query.filter_by(short_code=short_code).first()
    if url_map_entry:
        return render_template('analytics.html', url_data=url_map_entry)  # ✅ correct function name
    else:
        abort(404)
@app.route('/')
def index():
    all_urls = URLMap.query.order_by(URLMap.created_at.desc()).all()
    return render_template('index.html', url_data=all_urls)  # ✅ correct function name
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

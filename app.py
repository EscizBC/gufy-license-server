from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
import hashlib
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')

# Настройка PostgreSQL для Render
database_url = os.environ.get('DATABASE_URL')

if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///licenses.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}

db = SQLAlchemy(app)

# Модели базы данных
class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    hwid = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    activation_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_validation = db.Column(db.DateTime, nullable=True)
    expiry_date = db.Column(db.DateTime, nullable=True)

class ActivationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), nullable=False)
    hwid = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

# Создаем таблицы при запуске
with app.app_context():
    try:
        db.create_all()
        if not AdminUser.query.first():
            default_password = os.environ.get('ADMIN_PASSWORD', 'Pfizer!Soft2025')
            admin = AdminUser(
                username='admin',
                password_hash=hashlib.sha256(default_password.encode()).hexdigest()
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin created: admin /", default_password)
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

def check_all_licenses_expiry():
    """Проверяет все лицензии на истечение срока"""
    try:
        licenses = License.query.all()
        now = datetime.utcnow()
        expired_count = 0
        
        for license in licenses:
            if license.expiry_date and license.expiry_date < now and license.is_active:
                license.is_active = False
                expired_count += 1
                print(f"⏰ License {license.key} expired and deactivated")
        
        if expired_count > 0:
            db.session.commit()
            print(f"✅ Deactivated {expired_count} expired licenses")
            
        return expired_count
    except Exception as e:
        print(f"❌ Error checking licenses expiry: {e}")
        return 0

def is_license_expired(license_obj):
    """Проверяет истекла ли лицензия"""
    if not license_obj.expiry_date:
        return False
    
    now = datetime.utcnow()
    is_expired = license_obj.expiry_date < now
    
    # Немедленно деактивируем если истекла
    if is_expired and license_obj.is_active:
        license_obj.is_active = False
        db.session.commit()
        print(f"⏰ License {license_obj.key} automatically deactivated due to expiry")
    
    return is_expired

def get_local_time(utc_time):
    """Конвертирует UTC время в локальное (UTC+3)"""
    if not utc_time:
        return None
    return utc_time + timedelta(hours=3)

# API endpoints
@app.route('/license', methods=['POST'])
def license_api():
    # ПРИНУДИТЕЛЬНО проверяем ВСЕ лицензии при каждом запросе
    check_all_licenses_expiry()
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'})
            
        action = data.get('action')
        key = data.get('key')
        hwid = data.get('hwid')
        
        if not key:
            return jsonify({'success': False, 'error': 'No key provided'})
        
        if action == 'activate':
            return activate_license(key, hwid, request)
        elif action == 'validate':
            return validate_license(key, hwid)
        else:
            return jsonify({'success': False, 'error': 'Invalid action'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'})

def activate_license(key, hwid, request):
    try:
        license_obj = License.query.filter_by(key=key).first()
        
        if not license_obj:
            return jsonify({'success': False, 'error': 'Invalid license key'})
        
        # Проверяем конкретную лицензию
        if is_license_expired(license_obj):
            return jsonify({'success': False, 'error': 'License has expired and was deactivated'})
        
        if not license_obj.is_active:
            return jsonify({'success': False, 'error': 'License is deactivated'})
        
        if license_obj.hwid:
            if license_obj.hwid == hwid:
                return jsonify({
                    'success': True, 
                    'message': 'License already activated on this device',
                    'license_data': {'status': 'active'}
                })
            else:
                activation_req = ActivationRequest(
                    key=key,
                    hwid=hwid,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                db.session.add(activation_req)
                db.session.commit()
                
                return jsonify({
                    'success': False, 
                    'error': 'License already activated on another device. Activation request sent to admin.'
                })
        
        license_obj.hwid = hwid
        license_obj.activation_date = datetime.utcnow()
        license_obj.last_validation = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'License activated successfully',
            'license_data': {'status': 'active'}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f'Activation error: {str(e)}'})

def validate_license(key, hwid):
    try:
        license_obj = License.query.filter_by(key=key).first()
        
        if not license_obj:
            return jsonify({'valid': False, 'error': 'Invalid license key'})
        
        # Проверяем конкретную лицензию
        if is_license_expired(license_obj):
            return jsonify({'valid': False, 'error': 'License has expired and was deactivated'})
        
        if not license_obj.is_active:
            return jsonify({'valid': False, 'error': 'License is deactivated'})
        
        if not license_obj.hwid:
            return jsonify({'valid': False, 'error': 'License not activated'})
        
        if license_obj.hwid != hwid:
            return jsonify({'valid': False, 'error': 'License not valid for this device'})
        
        license_obj.last_validation = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'valid': True, 'message': 'License is valid'})
    except Exception as e:
        return jsonify({'valid': False, 'error': f'Validation error: {str(e)}'})

# Админ панель
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = AdminUser.query.filter_by(username=username).first()
        if admin and admin.password_hash == hashlib.sha256(password.encode()).hexdigest():
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        
        return render_template('admin_login.html', error='Invalid credentials')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        # ПРИНУДИТЕЛЬНО проверяем ВСЕ лицензии при загрузке админки
        expired_count = check_all_licenses_expiry()
        
        licenses = License.query.all()
        activation_requests = ActivationRequest.query.filter_by(status='pending').all()
        stats = {
            'total_licenses': License.query.count(),
            'activated_licenses': License.query.filter(License.hwid.isnot(None)).count(),
            'pending_requests': ActivationRequest.query.filter_by(status='pending').count()
        }
        
        now = datetime.utcnow()
        
        return render_template('admin_dashboard.html', 
                             licenses=licenses, 
                             activation_requests=activation_requests,
                             stats=stats,
                             now=now,
                             get_local_time=get_local_time)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500

@app.route('/admin/add_license', methods=['POST'])
def add_license():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    try:
        name = request.form.get('name')
        key = request.form.get('key')
        expiry_date_str = request.form.get('expiry_date')
        
        if not key:
            return jsonify({'success': False, 'error': 'No key provided'})
        
        if not (len(key) == 26 and key.startswith('PFIZER-')):
            return jsonify({'success': False, 'error': 'Invalid key format. Use: PFIZER-XXXX-XXXX-XXXX-XXXX'})
        
        if License.query.filter_by(key=key).first():
            return jsonify({'success': False, 'error': 'Key already exists'})
        
        expiry_date = None
        if expiry_date_str:
            try:
                if 'Z' not in expiry_date_str and '+' not in expiry_date_str:
                    expiry_date_str += 'Z'
                expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
            except ValueError as e:
                return jsonify({'success': False, 'error': f'Invalid expiry date format: {str(e)}'})
        
        license_obj = License(
            name=name,
            key=key,
            expiry_date=expiry_date
        )
        db.session.add(license_obj)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'License added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error adding license: {str(e)}'})

@app.route('/admin/bulk_add_licenses', methods=['POST'])
def bulk_add_licenses():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    try:
        keys_text = request.form.get('keys')
        if not keys_text:
            return jsonify({'success': False, 'error': 'No keys provided'})
        
        keys = [k.strip() for k in keys_text.split('\n') if k.strip()]
        added = 0
        errors = []
        
        for key in keys:
            if len(key) == 26 and key.startswith('PFIZER-'):
                if not License.query.filter_by(key=key).first():
                    license_obj = License(key=key)
                    db.session.add(license_obj)
                    added += 1
                else:
                    errors.append(f"Key {key} already exists")
            else:
                errors.append(f"Invalid key format: {key}")
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Added {added} licenses',
            'errors': errors
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error in bulk add: {str(e)}'})

@app.route('/admin/process_request/<int:request_id>', methods=['POST'])
def process_request(request_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    try:
        # Проверяем лицензии
        check_all_licenses_expiry()
        
        action = request.form.get('action')
        activation_req = ActivationRequest.query.get_or_404(request_id)
        
        if action == 'approve':
            license_obj = License.query.filter_by(key=activation_req.key).first()
            if license_obj:
                if is_license_expired(license_obj):
                    return jsonify({'success': False, 'error': 'Cannot approve - license has expired'})
                
                license_obj.hwid = activation_req.hwid
                license_obj.activation_date = datetime.utcnow()
                activation_req.status = 'approved'
                db.session.commit()
                return jsonify({'success': True, 'message': 'Request approved'})
            else:
                return jsonify({'success': False, 'error': 'License not found'})
        
        elif action == 'reject':
            activation_req.status = 'rejected'
            db.session.commit()
            return jsonify({'success': True, 'message': 'Request rejected'})
        
        return jsonify({'success': False, 'error': 'Invalid action'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error processing request: {str(e)}'})

@app.route('/admin/toggle_license/<int:license_id>', methods=['POST'])
def toggle_license(license_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    try:
        # Проверяем лицензии
        check_all_licenses_expiry()
        
        license_obj = License.query.get_or_404(license_id)
        
        if is_license_expired(license_obj) and not license_obj.is_active:
            return jsonify({'success': False, 'error': 'Cannot activate expired license'})
        
        license_obj.is_active = not license_obj.is_active
        db.session.commit()
        
        status = "activated" if license_obj.is_active else "deactivated"
        return jsonify({'success': True, 'message': f'License {status}'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error toggling license: {str(e)}'})

@app.route('/admin/delete_license/<int:license_id>', methods=['POST'])
def delete_license(license_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    try:
        license_obj = License.query.get_or_404(license_id)
        db.session.delete(license_obj)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'License deleted'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error deleting license: {str(e)}'})

# Специальный endpoint для принудительной проверки
@app.route('/admin/check_expired', methods=['POST'])
def check_expired():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    expired_count = check_all_licenses_expiry()
    return jsonify({'success': True, 'message': f'Checked licenses. Deactivated: {expired_count}'})

@app.route('/')
def index():
    return jsonify({
        'message': 'PFIZER License Server is running',
        'status': 'active',
        'version': '2.0',
        'database': 'PostgreSQL' if os.environ.get('DATABASE_URL') else 'SQLite'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
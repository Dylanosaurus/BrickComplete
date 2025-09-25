from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
import os
import requests
import urllib3
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime, UTC
from functools import wraps
from database_service import db_service

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///brickcomplete.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Simplified Database Models - Only the three required tables
class User(UserMixin, db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    user_inventories = db.relationship('UserInventory', backref='user', lazy=True)
    
    def get_id(self):
        return str(self.user_id)

class UserInventory(db.Model):
    """User-generated inventory for a set"""
    user_inventory_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    set_number = db.Column(db.String(20), nullable=False)
    inventory_name = db.Column(db.String(200), nullable=False)  # e.g., "My Custom Build", "Modified Version"
    description = db.Column(db.Text, nullable=True)
    is_public = db.Column(db.Boolean, default=False)  # Allow sharing with other users
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # Relationships
    parts = db.relationship('UserInventoryPart', backref='user_inventory', cascade='all, delete-orphan')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'set_number', 'inventory_name'),)
    
    def __repr__(self):
        return f'<UserInventory {self.inventory_name} - {self.set_number}>'

class UserInventoryPart(db.Model):
    """Parts in a user-generated inventory"""
    user_inventory_part_id = db.Column(db.Integer, primary_key=True)
    user_inventory_id = db.Column(db.Integer, db.ForeignKey('user_inventory.user_inventory_id'), nullable=False)
    part_number = db.Column(db.String(50), nullable=False)
    part_name = db.Column(db.String(200), nullable=False)
    color_id = db.Column(db.Integer, nullable=False)
    color_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    is_spare = db.Column(db.Boolean, default=False)
    is_minifig_part = db.Column(db.Boolean, default=False)  # Indicates if this part belongs to a minifigure
    part_image_url = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.Text, nullable=True)  # User notes about this part
    
    __table_args__ = (db.UniqueConstraint('user_inventory_id', 'part_number', 'color_id'),)
    
    def __repr__(self):
        return f'<UserInventoryPart {self.part_number} ({self.color_name}) - Qty: {self.quantity}>'

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def login_required_json(f):
    """Custom decorator that returns JSON error for AJAX requests when user is not logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'error': 'You must be logged in to perform this action. Please log in and try again.',
                    'login_required': True
                }), 401
            else:
                return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_set_info(set_number):
    """Get set information from local database"""
    try:
        return db_service.get_set_info(set_number)
    except Exception as e:
        print(f"Database error getting set info: {e}")
        return None

def get_set_inventory(set_number):
    """Get inventory for a LEGO set from local database"""
    try:
        # Get set information
        set_info = db_service.get_set_info(set_number)
        if not set_info:
            return None
        
        # Get inventory from database
        inventory = db_service.get_set_inventory(set_number)
        
        return {
            'set_number': set_number,
            'set_name': set_info['set_name'],
            'set_image': set_info['set_image'],
            'set_url': set_info['set_url'],
            'year': set_info['year'],
            'num_parts': set_info['num_parts'],
            'inventory': inventory
        }
    except Exception as e:
        print(f"Database error getting set inventory: {e}")
        return None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(user_name=form.username.data).first()
        if user and user.password == form.password.data:  # In production, use proper password hashing
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(user_name=form.username.data).first():
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': False,
                    'message': 'Username already exists',
                    'errors': {'username': ['Username already exists']}
                }), 400
            else:
                flash('Username already exists')
                return render_template('register.html', form=form)
        
        user = User(user_name=form.username.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        
        # Automatically log in the user after successful registration
        login_user(user)
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'success': True,
                'message': 'Registration successful! You are now logged in.',
                'redirect': url_for('index')
            })
        else:
            flash('Registration successful! You are now logged in.')
            return redirect(url_for('index'))
    
    # Handle form validation errors for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Content-Type') == 'application/json':
        if not form.validate_on_submit():
            return jsonify({
                'success': False,
                'message': 'Please correct the errors below',
                'errors': form.errors
            }), 400
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/search_set', methods=['POST'])
def search_set():
    set_number = request.json.get('set_number')
    if not set_number:
        return jsonify({'error': 'Set number is required'}), 400
    
    inventory_data = get_set_inventory(set_number)
    
    if inventory_data:
        return jsonify(inventory_data)
    else:
        return jsonify({'error': 'Failed to fetch set inventory'}), 500

@app.route('/get_set_suggestions')
def get_set_suggestions():
    """Get set number suggestions from the database"""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)
    
    if len(query) < 2:
        return jsonify([])
    
    try:
        suggestions = db_service.get_set_suggestions(query, limit)
        return jsonify(suggestions)
    except Exception as e:
        print(f"Error getting set suggestions: {e}")
        return jsonify([])

@app.route('/my_collection')
@login_required
def my_collection():
    user_inventories = UserInventory.query.filter_by(user_id=current_user.user_id).order_by(UserInventory.created_at.desc()).all()
    
    # Convert user inventories to the format expected by the template
    user_sets = []
    for inventory in user_inventories:
        # Get set info from the LEGO database
        set_info = db_service.get_set_info(inventory.set_number)
        
        user_sets.append({
            'owned_set_id': inventory.user_inventory_id,  # Use inventory_id as owned_set_id
            'custom_display_name': inventory.inventory_name,
            'set_number': inventory.set_number,
            'added_at': inventory.created_at,
            'set': {
                'set_name': set_info['set_name'] if set_info else f'Set {inventory.set_number}',
                'set_image': set_info['set_image'] if set_info else '',
                'set_url': set_info['set_url'] if set_info else '',
                'year': set_info['year'] if set_info else None,
                'num_parts': set_info['num_parts'] if set_info else 0
            } if set_info else None
        })
    
    return render_template('my_collection.html', user_sets=user_sets)

# New API endpoints for user inventories
@app.route('/create_user_inventory', methods=['POST'])
@login_required_json
def create_user_inventory():
    data = request.json
    set_number = data.get('set_number')
    inventory_name = data.get('inventory_name')
    description = data.get('description', '')
    is_public = data.get('is_public', False)
    
    if not set_number or not inventory_name:
        return jsonify({'error': 'Set number and inventory name are required'}), 400
    
    # Check if this inventory name already exists for this user and set
    existing = UserInventory.query.filter_by(
        user_id=current_user.user_id,
        set_number=set_number,
        inventory_name=inventory_name
    ).first()
    
    if existing:
        return jsonify({'error': 'An inventory with this name already exists for this set'}), 400
    
    # Create new user inventory
    new_inventory = UserInventory(
        user_id=current_user.user_id,
        set_number=set_number,
        inventory_name=inventory_name,
        description=description,
        is_public=is_public
    )
    db.session.add(new_inventory)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'User inventory created successfully',
        'user_inventory_id': new_inventory.user_inventory_id
    })

@app.route('/get_user_inventories/<set_number>')
@login_required_json
def get_user_inventories(set_number):
    user_inventories = UserInventory.query.filter_by(
        user_id=current_user.user_id,
        set_number=set_number
    ).all()
    
    result = []
    for inventory in user_inventories:
        result.append({
            'user_inventory_id': inventory.user_inventory_id,
            'inventory_name': inventory.inventory_name,
            'description': inventory.description,
            'is_public': inventory.is_public,
            'created_at': inventory.created_at.isoformat(),
            'updated_at': inventory.updated_at.isoformat(),
            'part_count': len(inventory.parts)
        })
    
    return jsonify(result)

@app.route('/add_part_to_inventory', methods=['POST'])
@login_required_json
def add_part_to_inventory():
    data = request.json
    user_inventory_id = data.get('user_inventory_id')
    part_number = data.get('part_number')
    part_name = data.get('part_name')
    color_id = data.get('color_id')
    color_name = data.get('color_name')
    quantity = data.get('quantity', 1)
    is_spare = data.get('is_spare', False)
    is_minifig_part = data.get('is_minifig_part', False)
    part_image_url = data.get('part_image_url', '')
    notes = data.get('notes', '')
    
    if not all([user_inventory_id, part_number, part_name, color_id, color_name]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Verify the inventory belongs to the current user
    inventory = UserInventory.query.filter_by(
        user_inventory_id=user_inventory_id,
        user_id=current_user.user_id
    ).first()
    
    if not inventory:
        return jsonify({'error': 'Inventory not found or access denied'}), 404
    
    # Check if this part already exists in the inventory
    existing_part = UserInventoryPart.query.filter_by(
        user_inventory_id=user_inventory_id,
        part_number=part_number,
        color_id=color_id
    ).first()
    
    if existing_part:
        # Update existing part
        existing_part.quantity = quantity
        existing_part.is_spare = is_spare
        existing_part.is_minifig_part = is_minifig_part
        existing_part.notes = notes
        if part_image_url:
            existing_part.part_image_url = part_image_url
    else:
        # Create new part
        new_part = UserInventoryPart(
            user_inventory_id=user_inventory_id,
            part_number=part_number,
            part_name=part_name,
            color_id=color_id,
            color_name=color_name,
            quantity=quantity,
            is_spare=is_spare,
            is_minifig_part=is_minifig_part,
            part_image_url=part_image_url,
            notes=notes
        )
        db.session.add(new_part)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Part added to inventory successfully'})

@app.route('/get_inventory_parts/<int:user_inventory_id>')
@login_required_json
def get_inventory_parts(user_inventory_id):
    # Verify the inventory belongs to the current user
    inventory = UserInventory.query.filter_by(
        user_inventory_id=user_inventory_id,
        user_id=current_user.user_id
    ).first()
    
    if not inventory:
        return jsonify({'error': 'Inventory not found or access denied'}), 404
    
    parts = []
    for part in inventory.parts:
        parts.append({
            'user_inventory_part_id': part.user_inventory_part_id,
            'part_number': part.part_number,
            'part_name': part.part_name,
            'color_id': part.color_id,
            'color_name': part.color_name,
            'quantity': part.quantity,
            'is_spare': part.is_spare,
            'is_minifig_part': part.is_minifig_part,
            'part_image_url': part.part_image_url,
            'notes': part.notes
        })
    
    return jsonify({
        'inventory': {
            'user_inventory_id': inventory.user_inventory_id,
            'set_number': inventory.set_number,
            'inventory_name': inventory.inventory_name,
            'description': inventory.description,
            'is_public': inventory.is_public,
            'created_at': inventory.created_at.isoformat(),
            'updated_at': inventory.updated_at.isoformat()
        },
        'parts': parts
    })

@app.route('/delete_user_inventory', methods=['POST'])
@login_required_json
def delete_user_inventory():
    data = request.json
    user_inventory_id = data.get('user_inventory_id')
    
    if not user_inventory_id:
        return jsonify({'error': 'Inventory ID is required'}), 400
    
    # Find the inventory
    inventory = UserInventory.query.filter_by(
        user_inventory_id=user_inventory_id,
        user_id=current_user.user_id
    ).first()
    
    if not inventory:
        return jsonify({'error': 'Inventory not found'}), 404
    
    # Delete the inventory (parts will be deleted automatically due to cascade)
    db.session.delete(inventory)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Inventory deleted successfully'})

# Legacy endpoints for frontend compatibility
@app.route('/add_to_collection', methods=['POST'])
@login_required_json
def add_to_collection():
    """Legacy endpoint - creates a user inventory with default name"""
    data = request.json
    set_number = data.get('set_number')
    set_name = data.get('set_name')
    instance_name = data.get('instance_name', 'Default')
    
    if not set_number or not set_name:
        return jsonify({'error': 'Set number and name are required'}), 400
    
    # Check if this inventory name already exists for this user and set
    existing = UserInventory.query.filter_by(
        user_id=current_user.user_id,
        set_number=set_number,
        inventory_name=instance_name
    ).first()
    
    if existing:
        return jsonify({'error': 'This set instance already exists in your collection'}), 400
    
    # Create new user inventory
    new_inventory = UserInventory(
        user_id=current_user.user_id,
        set_number=set_number,
        inventory_name=instance_name,
        description=f'Collection instance for {set_name}',
        is_public=False
    )
    db.session.add(new_inventory)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Set added to collection successfully',
        'owned_set_id': new_inventory.user_inventory_id  # Use inventory_id as owned_set_id for compatibility
    })

@app.route('/get_user_sets/<set_number>')
@login_required_json
def get_user_sets(set_number):
    """Legacy endpoint - returns user inventories for a set as if they were owned sets"""
    user_inventories = UserInventory.query.filter_by(
        user_id=current_user.user_id,
        set_number=set_number
    ).all()
    
    result = []
    for inventory in user_inventories:
        result.append({
            'id': inventory.user_inventory_id,  # Use inventory_id as id for compatibility
            'set_number': inventory.set_number,
            'instance_name': inventory.inventory_name,
            'added_at': inventory.created_at.isoformat()
        })
    
    return jsonify(result)

@app.route('/delete_set_instance', methods=['POST'])
@login_required_json
def delete_set_instance():
    """Legacy endpoint - deletes a user inventory"""
    data = request.json
    owned_set_id = data.get('owned_set_id')  # This is actually user_inventory_id
    
    if not owned_set_id:
        return jsonify({'error': 'Collection ID is required'}), 400
    
    # Find the inventory
    inventory = UserInventory.query.filter_by(
        user_inventory_id=owned_set_id,
        user_id=current_user.user_id
    ).first()
    
    if not inventory:
        return jsonify({'error': 'Set instance not found'}), 404
    
    # Delete the inventory (parts will be deleted automatically due to cascade)
    db.session.delete(inventory)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Set instance deleted successfully'})

@app.route('/remove_from_collection', methods=['POST'])
@login_required_json
def remove_from_collection():
    """Legacy endpoint - same as delete_set_instance"""
    return delete_set_instance()

@app.route('/view_instance_inventory', methods=['POST'])
@login_required_json
def view_instance_inventory():
    """Legacy endpoint - returns inventory data for a specific instance"""
    data = request.json
    set_number = data.get('set_number')
    instance_name = data.get('instance_name', 'Default')
    
    if not set_number:
        return jsonify({'error': 'Set number is required'}), 400
    
    # Get inventory data from the LEGO database
    inventory_data = get_set_inventory(set_number)
    
    if inventory_data:
        # Add instance information to the response
        inventory_data['instance_name'] = instance_name
        return jsonify(inventory_data)
    else:
        return jsonify({'error': 'Failed to fetch set inventory'}), 500

@app.route('/get_modified_inventory/<set_number>')
@login_required_json
def get_modified_inventory(set_number):
    """Legacy endpoint - returns modified inventory for a specific instance"""
    instance_name = request.args.get('instance_name', 'Default')
    
    # Find the user inventory
    inventory = UserInventory.query.filter_by(
        user_id=current_user.user_id,
        set_number=set_number,
        inventory_name=instance_name
    ).first()
    
    if not inventory:
        return jsonify({})  # Return empty object if no modifications
    
    # Build the modifications object
    modifications = {}
    for part in inventory.parts:
        # Use the new part key format: part_number_color_id_spare_status_minifig_status
        key = f"{part.part_number}_{part.color_id}_{'spare' if part.is_spare else 'regular'}_{'minifig' if part.is_minifig_part else 'normal'}"
        modifications[key] = part.quantity
    
    return jsonify(modifications)

@app.route('/update_inventory', methods=['POST'])
@login_required_json
def update_inventory():
    """Legacy endpoint - updates inventory modifications for a specific instance"""
    data = request.json
    set_number = data.get('set_number')
    instance_name = data.get('instance_name', 'Default')
    
    print(f"DEBUG: Received update_inventory request for set {set_number}, instance {instance_name}")
    print(f"DEBUG: Modifications data: {data.get('modifications', {})}")
    
    if not set_number:
        return jsonify({'error': 'Set number is required'}), 400
    
    # Find the user inventory
    inventory = UserInventory.query.filter_by(
        user_id=current_user.user_id,
        set_number=set_number,
        inventory_name=instance_name
    ).first()
    
    if not inventory:
        return jsonify({'error': 'Instance not found'}), 404
    
    # Handle batch modifications
    if 'modifications' in data:
        modifications = data.get('modifications', {})
        
        # Clear existing parts
        UserInventoryPart.query.filter_by(user_inventory_id=inventory.user_inventory_id).delete()
        
        # Add new parts
        for part_key, quantity in modifications.items():
            if quantity != 0:  # Only save non-zero modifications
                print(f"DEBUG: Processing part_key: {part_key}, quantity: {quantity}")
                # Parse the new part key format: part_number_color_id_spare_status_minifig_status
                key_parts = part_key.split('_')
                if len(key_parts) >= 4:
                    part_number = key_parts[0]
                    color_id = int(key_parts[1])
                    is_spare = key_parts[2] == 'spare'
                    is_minifig_part = key_parts[3] == 'minifig'
                    print(f"DEBUG: Parsed - part_number: {part_number}, color_id: {color_id}, is_spare: {is_spare}, is_minifig_part: {is_minifig_part}")
                else:
                    # Fallback for old format
                    part_number = key_parts[0]
                    color_id = int(key_parts[1])
                    is_spare = False
                    is_minifig_part = False
                    print(f"DEBUG: Using fallback format - part_number: {part_number}, color_id: {color_id}")
                
                # Get part info from LEGO database
                lego_inventory = db_service.get_set_inventory(set_number)
                part_info = None
                for part in lego_inventory:
                    if part['part_number'] == part_number and part['color_id'] == color_id:
                        part_info = part
                        break
                
                if part_info:
                    new_part = UserInventoryPart(
                        user_inventory_id=inventory.user_inventory_id,
                        part_number=part_number,
                        part_name=part_info['part_name'],
                        color_id=color_id,
                        color_name=part_info['color_name'],
                        quantity=quantity,
                        is_spare=is_spare,
                        is_minifig_part=is_minifig_part,
                        part_image_url=part_info.get('part_image_url', '')
                    )
                    db.session.add(new_part)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Inventory saved successfully'})
    
    return jsonify({'error': 'No modifications provided'}), 400

@app.route('/check_instructions', methods=['POST'])
def check_instructions():
    """Check if building instructions exist for a set"""
    data = request.json
    set_number = data.get('set_number')
    
    if not set_number:
        return jsonify({'error': 'Set number required'}), 400
    
    try:
        # Construct the LEGO building instructions URL
        instructions_url = f"https://www.lego.com/en-us/service/building-instructions/{set_number}"
        # Make a GET request to get the page content
        # Disable SSL verification for development (not recommended for production)
        response = requests.get(instructions_url, timeout=15, allow_redirects=True, verify=False)
        
        # Check if the response is successful (200-299 range)
        if response.status_code != 200:
            return jsonify({
                'has_instructions': False,
                'status_code': response.status_code,
                'url': instructions_url
            })
        
        # Parse the HTML content to look for the specific data-test attribute
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for element with data-test="select-instruction-heading"
        instruction_heading = soup.find(attrs={'data-test': 'select-instruction-heading'})
        
        has_instructions = instruction_heading is not None
        
        return jsonify({
            'has_instructions': has_instructions,
            'status_code': response.status_code,
            'url': instructions_url
        })
        
    except requests.exceptions.RequestException as e:
        # If there's an error (network issue, timeout, etc.), assume no instructions
        return jsonify({
            'has_instructions': False,
            'error': str(e)
        })
    except Exception as e:
        return jsonify({
            'has_instructions': False,
            'error': f'Parsing error: {str(e)}'
        })

@app.route('/get_instruction_images', methods=['POST'])
def get_instruction_images():
    """Scrape building instruction images from brickinstructions.com"""
    data = request.json
    set_number = data.get('set_number')
    
    if not set_number:
        return jsonify({'error': 'Set number required'}), 400
    
    try:
        # Construct the brickinstructions.com URL
        instructions_url = f"https://lego.brickinstructions.com/lego_instructions/set/{set_number}"
        
        # Make a request to get the page content
        response = requests.get(instructions_url, timeout=15, verify=False)
        
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Page not found (status: {response.status_code})'
            })
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the instructionscontainer div
        instructions_container = soup.find('div', {'id': 'instructionsContainer'})
        
        if not instructions_container:
            return jsonify({
                'success': False,
                'error': 'Instructions container not found'
            })
        
        # Find all images in the container
        images = instructions_container.find_all('img')
        
        if not images:
            return jsonify({
                'success': False,
                'error': 'No instruction images found'
            })
        
        # Extract image URLs
        image_urls = []
        for img in images:
            src = img.get('src')
            if src:
                # Convert relative URLs to absolute URLs
                if src.startswith('/'):
                    src = f"https://lego.brickinstructions.com{src}"
                elif not src.startswith('http'):
                    src = f"https://lego.brickinstructions.com/{src}"
                
                # Replace "thumbnails" with "instructions" for higher quality images
                src = src.replace('thumbnails', 'instructions')
                
                image_urls.append(src)
        
        return jsonify({
            'success': True,
            'images': image_urls,
            'count': len(image_urls),
            'url': instructions_url
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'Network error: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Parsing error: {str(e)}'
        })

@app.route('/update_inventory_name', methods=['POST'])
@login_required_json
def update_inventory_name():
    """Update the name of a user inventory"""
    data = request.json
    user_inventory_id = data.get('user_inventory_id')
    new_name = data.get('new_name')
    
    if not user_inventory_id or not new_name:
        return jsonify({'error': 'Missing required fields'}), 400
    
    if len(new_name.strip()) == 0:
        return jsonify({'error': 'Name cannot be empty'}), 400
    
    try:
        # Find the inventory
        inventory = UserInventory.query.filter_by(
            user_inventory_id=user_inventory_id,
            user_id=current_user.user_id
        ).first()
        
        if not inventory:
            return jsonify({'error': 'Inventory not found'}), 404
        
        # Check if another inventory with the same set number and name already exists
        existing_inventory = UserInventory.query.filter_by(
            set_number=inventory.set_number,
            inventory_name=new_name.strip(),
            user_id=current_user.user_id
        ).filter(UserInventory.user_inventory_id != user_inventory_id).first()
        
        if existing_inventory:
            return jsonify({'error': 'An instance with this name already exists for this set'}), 400
        
        # Update the name
        inventory.inventory_name = new_name.strip()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Inventory name updated successfully',
            'new_name': inventory.inventory_name
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update inventory name: {str(e)}'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

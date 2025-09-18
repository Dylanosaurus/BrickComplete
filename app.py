from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, UTC
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///brickcomplete.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Bricklink API configuration
BRICKLINK_API_URL = 'https://api.bricklink.com/api/store/v1'
BRICKLINK_TOKEN = "4D800F0F84214B858EB0A133F49B57C8"
BRICKLINK_SECRET = "D0637A8BBCD7407C857A583C220A50A6"

# Database Models
class User(UserMixin, db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    owned_sets = db.relationship('OwnedSet', backref='user', lazy=True)
    
    def get_id(self):
        return str(self.user_id)

class Theme(db.Model):
    theme_id = db.Column(db.Integer, primary_key=True)
    theme_name = db.Column(db.String(100), nullable=False)
    parent_theme_id = db.Column(db.Integer, db.ForeignKey('theme.theme_id'), nullable=True)
    sets = db.relationship('Set', backref='theme', lazy=True)
    parent_theme = db.relationship('Theme', remote_side=[theme_id], backref='subthemes')
    
    def __repr__(self):
        return f'<Theme {self.theme_id} - {self.theme_name}>'

class PartCategory(db.Model):
    part_category_id = db.Column(db.Integer, primary_key=True)
    part_category_name = db.Column(db.String(100), nullable=False)
    parts = db.relationship('Part', backref='part_category', lazy=True)
    
    def __repr__(self):
        return f'<PartCategory {self.part_category_id} - {self.part_category_name}>'

class Set(db.Model):
    set_number = db.Column(db.String(20), primary_key=True)
    set_name = db.Column(db.String(200), nullable=False)
    theme_id = db.Column(db.Integer, db.ForeignKey('theme.theme_id'), nullable=True)
    year = db.Column(db.Integer, nullable=True)
    image = db.Column(db.String(500), nullable=True)
    set_image = db.Column(db.String(500), nullable=True)
    set_url = db.Column(db.String(500), nullable=True)
    num_parts = db.Column(db.Integer, nullable=True)
    original_inventories = db.relationship('OriginalSetInventory', backref='set', lazy=True)
    
    def __repr__(self):
        return f'<Set {self.set_number} - {self.set_name}>'

class OwnedSet(db.Model):
    owned_set_id = db.Column(db.Integer, primary_key=True)
    custom_display_name = db.Column(db.String(200), nullable=False)
    set_number = db.Column(db.String(20), db.ForeignKey('set.set_number'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    owned_inventories = db.relationship('OwnedSetInventory', backref='owned_set', lazy=True)
    set = db.relationship('Set', backref='owned_sets')
    
    def __repr__(self):
        return f'<OwnedSet {self.custom_display_name} - {self.set_number}>'

class Part(db.Model):
    part_number = db.Column(db.String(50), primary_key=True)
    part_name = db.Column(db.String(200), nullable=False)
    part_image = db.Column(db.String(500), nullable=True)
    part_category_id = db.Column(db.Integer, db.ForeignKey('part_category.part_category_id'), nullable=True)
    original_inventories = db.relationship('OriginalSetInventory', backref='part', lazy=True)
    
    def __repr__(self):
        return f'<Part {self.part_number} - {self.part_name}>'

class Color(db.Model):
    color_id = db.Column(db.Integer, primary_key=True)
    color_name = db.Column(db.String(100), nullable=False)
    original_inventories = db.relationship('OriginalSetInventory', backref='color', lazy=True)
    
    def __repr__(self):
        return f'<Color {self.color_id} - {self.color_name}>'

class OriginalSetInventory(db.Model):
    inventory_part_id = db.Column(db.Integer, primary_key=True)
    set_number = db.Column(db.String(20), db.ForeignKey('set.set_number'), nullable=False)
    part_number = db.Column(db.String(50), db.ForeignKey('part.part_number'), nullable=False)
    color_id = db.Column(db.Integer, db.ForeignKey('color.color_id'), nullable=False)
    is_spare = db.Column(db.Boolean, default=False)
    quantity = db.Column(db.Integer, nullable=False)
    
    __table_args__ = (db.UniqueConstraint('set_number', 'part_number', 'color_id'),)
    
    def __repr__(self):
        return f'<OriginalSetInventory {self.set_number} - {self.part_number} ({self.color_id})>'

class OwnedSetInventory(db.Model):
    modification_id = db.Column(db.Integer, primary_key=True)
    owned_set_id = db.Column(db.Integer, db.ForeignKey('owned_set.owned_set_id'), nullable=False)
    inventory_part_id = db.Column(db.Integer, db.ForeignKey('original_set_inventory.inventory_part_id'), nullable=False)
    actual_quantity = db.Column(db.Integer, nullable=False)
    original_inventory = db.relationship('OriginalSetInventory', backref='owned_inventories')
    
    __table_args__ = (db.UniqueConstraint('owned_set_id', 'inventory_part_id'),)
    
    def __repr__(self):
        return f'<OwnedSetInventory {self.owned_set_id} - {self.inventory_part_id}: {self.actual_quantity}>'

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

# Bricklink API helper functions
import hmac
import hashlib
import time
import urllib.parse
import base64
import json

def generate_oauth_signature(method, url, params, consumer_secret, token_secret):
    """Generate OAuth 1.0a signature for Bricklink API"""
    # Create parameter string
    param_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    
    # Create signature base string
    signature_base_string = f"{method}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_string, safe='')}"
    
    # Create signing key
    signing_key = f"{urllib.parse.quote(consumer_secret, safe='')}&{urllib.parse.quote(token_secret, safe='')}"
    
    # Generate signature
    signature = hmac.new(
        signing_key.encode('utf-8'),
        signature_base_string.encode('utf-8'),
        hashlib.sha1
    ).digest()
    
    return base64.b64encode(signature).decode('utf-8')

def make_bricklink_request(endpoint, method='GET', data=None):
    """Make authenticated request to Bricklink API"""
    try:
        # OAuth parameters
        timestamp = str(int(time.time()))
        nonce = str(int(time.time() * 1000))
        
        # Your Bricklink API credentials
        consumer_key = "9C2AE61850DC4F209D6C38748F538611"
        consumer_secret = "9C2163AD7951438C8449AF5275875756"
        
        url = f"{BRICKLINK_API_URL}{endpoint}"
        
        # OAuth parameters
        oauth_params = {
            'oauth_consumer_key': consumer_key,
            'oauth_token': BRICKLINK_TOKEN,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': timestamp,
            'oauth_nonce': nonce,
            'oauth_version': '1.0'
        }
        
        # Generate signature
        oauth_params['oauth_signature'] = generate_oauth_signature(
            method, url, oauth_params, consumer_secret, BRICKLINK_SECRET
        )
        
        # Create Authorization header
        auth_header = 'OAuth ' + ', '.join([f'{k}="{v}"' for k, v in oauth_params.items()])
        
        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
        
        # Make request
        if method == 'GET':
            response = requests.get(url, headers=headers)
        else:
            response = requests.post(url, headers=headers, json=data)
        
        return response
    except Exception as e:
        print(f"Error making Bricklink API request: {e}")
        return None

def store_original_inventory(set_number, set_name, inventory, set_image=None, year=None, num_parts=None, set_url=None):
    """Store the original inventory in the database"""
    try:
        # Check if original inventory already exists for this set
        existing_count = OriginalSetInventory.query.filter_by(set_number=set_number).count()
        if existing_count > 0:
            print(f"Original inventory for set {set_number} already exists in database ({existing_count} parts)")
            return
        
        # Create or get the set record
        set_record = db.session.get(Set, set_number)
        if not set_record:
            set_record = Set(
                set_number=set_number,
                set_name=set_name,
                theme_id=None,  # Will be set later when theme data is available
                year=year,
                image=None,
                set_image=set_image,
                set_url=set_url,
                num_parts=num_parts or len(inventory)
            )
            db.session.add(set_record)
        else:
            # Update existing set record with new information
            if set_image and not set_record.set_image:
                set_record.set_image = set_image
            if set_url and not set_record.set_url:
                set_record.set_url = set_url
            if year and not set_record.year:
                set_record.year = year
            if num_parts and not set_record.num_parts:
                set_record.num_parts = num_parts
        
        # Store each part in the original inventory
        for part_data in inventory:
            # Check if this specific part already exists in the original inventory
            existing_part = OriginalSetInventory.query.filter_by(
                set_number=set_number,
                part_number=part_data['part_number'],
                color_id=part_data['color_id']
            ).first()
            
            if existing_part:
                # Update quantity and is_spare if different
                if existing_part.quantity != part_data['quantity']:
                    existing_part.quantity = part_data['quantity']
                if existing_part.is_spare != part_data.get('is_spare', False):
                    existing_part.is_spare = part_data.get('is_spare', False)
                continue  # Skip adding this part since it already exists
            
            # Create or get the part record
            part_record = db.session.get(Part, part_data['part_number'])
            if not part_record:
                part_record = Part(
                    part_number=part_data['part_number'],
                    part_name=part_data['part_name'],
                    part_image=part_data.get('part_image_url'),
                    part_category_id=None  # Will be set later when category data is available
                )
                db.session.add(part_record)
            
            # Create or get the color record
            color_record = db.session.get(Color, part_data['color_id'])
            if not color_record:
                color_record = Color(
                    color_id=part_data['color_id'],
                    color_name=part_data['color_name']
                )
                db.session.add(color_record)
            
            # Create the original inventory record
            original_part = OriginalSetInventory(
                set_number=set_number,
                part_number=part_data['part_number'],
                color_id=part_data['color_id'],
                is_spare=part_data.get('is_spare', False),
                quantity=part_data['quantity']
            )
            db.session.add(original_part)
        
        db.session.commit()
        print(f"Stored original inventory for set {set_number} with {len(inventory)} parts")
    except Exception as e:
        print(f"Error storing original inventory for set {set_number}: {e}")
        db.session.rollback()
        # Re-raise the exception so the calling function knows it failed
        raise

def get_original_inventory(set_number):
    """Get the original inventory for a set from the database"""
    try:
        original_parts = OriginalSetInventory.query.filter_by(set_number=set_number).all()
        inventory = []
        for part in original_parts:
            inventory.append({
                'part_number': part.part_number,
                'part_name': part.part.part_name,
                'color_id': part.color_id,
                'color_name': part.color.color_name,
                'quantity': part.quantity,
                'is_spare': part.is_spare,
                'part_image_url': part.part.part_image,
            })
        return inventory
    except Exception as e:
        print(f"Error getting original inventory: {e}")
        return []

def get_set_info(set_number):
    """Get set information including image from Rebrickable API"""
    try:
        # Clean set number for API call
        rebrickable_url = f"https://rebrickable.com/api/v3/lego/sets/{set_number}/"
        headers = {
            'Authorization': 'key 104eafe954cd008af92cf77a83a22cac',
            'Accept': 'application/json'
        }
        
        response = requests.get(rebrickable_url, headers=headers, timeout=10)
        print(f"Set info API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Set info API data keys: {list(data.keys())}")
            
            return {
                'set_number': data.get('set_num', set_number),
                'set_name': data.get('name', f'LEGO Set {set_number}'),
                'year': data.get('year'),
                'num_parts': data.get('num_parts'),
                'set_image': data.get('set_img_url', ''),
                'set_url': data.get('set_url', ''),
                'theme_id': data.get('theme_id'),
                'theme_name': data.get('theme_name', '')
            }
        else:
            print(f"Set info API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Set info API failed: {e}")
        return None

def get_set_inventory(set_number):
    """Get inventory for a LEGO set from various sources"""
    try:
        # First, try to get set information
        set_info = get_set_info(set_number)
        
        # Method 1: Try Rebrickable API with your API key (most reliable)
        print(f"Trying Rebrickable API for set {set_number}")
        try:
            rebrickable_url = f"https://rebrickable.com/api/v3/lego/sets/{set_number}/parts/"
            headers = {
                'Authorization': 'key 104eafe954cd008af92cf77a83a22cac',
                'Accept': 'application/json'
            }
            
            response = requests.get(rebrickable_url, headers=headers, timeout=10)
            print(f"Rebrickable API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Rebrickable API data keys: {list(data.keys())}")
                
                if 'results' in data and data['results']:
                    inventory = []
                    for item in data['results']:
                        part_data = item.get('part', {})
                        color_data = item.get('color', {})
                        
                        inventory.append({
                            'part_number': part_data.get('part_num', ''),
                            'part_name': part_data.get('name', ''),
                            'color_id': color_data.get('id', 0),
                            'color_name': color_data.get('name', 'Unknown'),
                            'quantity': item.get('quantity', 0),
                            'is_spare': item.get('is_spare', False),
                            'part_image_url': part_data.get('part_img_url', ''),
                        })
                    
                    print(f"Successfully fetched {len(inventory)} parts from Rebrickable API")
                    
                    # Use set info if available, otherwise use defaults
                    if set_info:
                        set_name = set_info['set_name']
                        set_image = set_info['set_image']
                        set_url = set_info['set_url']
                        year = set_info['year']
                        num_parts = set_info['num_parts']
                    else:
                        set_name = f'LEGO Set {set_number}'
                        set_image = ''
                        set_url = ''
                        year = None
                        num_parts = len(inventory)
                    
                    # Store original inventory in database with set info
                    store_original_inventory(set_number, set_name, inventory, set_image, year, num_parts, set_url)
                    
                    return {
                        'set_number': set_number,
                        'set_name': set_name,
                        'set_image': set_image,
                        'set_url': set_url,
                        'year': year,
                        'num_parts': num_parts,
                        'inventory': inventory
                    }
                else:
                    print("No results found in Rebrickable API response")
            else:
                print(f"Rebrickable API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Rebrickable API failed: {e}")
        
        # Method 2: Try web scraping from Bricklink
        print(f"Trying web scraping for set {set_number}")
        try:
            from bs4 import BeautifulSoup
            import re
            
            url = f"https://www.bricklink.com/v2/catalog/catalogitem.page?S={set_number}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for inventory table
                inventory_table = soup.find('table', {'id': 'item-inventory'})
                if inventory_table:
                    inventory = []
                    rows = inventory_table.find_all('tr')[1:]  # Skip header row
                    
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            part_number = cells[0].get_text(strip=True)
                            part_name = cells[1].get_text(strip=True)
                            color_name = cells[2].get_text(strip=True)
                            quantity_text = cells[3].get_text(strip=True)
                            
                            # Extract quantity number
                            quantity_match = re.search(r'(\d+)', quantity_text)
                            quantity = int(quantity_match.group(1)) if quantity_match else 0
                            
                            # Check if it's a spare part
                            is_spare = 'spare' in quantity_text.lower()
                            
                            # Map common color names to IDs
                            color_id = get_color_id(color_name)
                            
                            # Get part image URL from Rebrickable
                            part_image_url = f"https://cdn.rebrickable.com/media/parts/ldraw/{part_number}.png"
                            
                            inventory.append({
                                'part_number': part_number,
                                'part_name': part_name,
                                'color_id': color_id,
                                'color_name': color_name,
                                'quantity': quantity,
                                'is_spare': is_spare,
                                'part_image_url': part_image_url,
                            })
                    
                    if inventory:
                        return {
                            'set_number': set_number,
                            'set_name': set_info['set_name'] if set_info else f'LEGO Set {set_number}',
                            'set_image': set_info['set_image'] if set_info else '',
                            'set_url': set_info['set_url'] if set_info else '',
                            'year': set_info['year'] if set_info else None,
                            'num_parts': set_info['num_parts'] if set_info else len(inventory),
                            'inventory': inventory
                        }
        except Exception as e:
            print(f"Web scraping failed: {e}")
        
        # Method 3: Try alternative scraping approach
        print(f"Trying alternative scraping for set {set_number}")
        try:
            from bs4 import BeautifulSoup
            
            url = f"https://www.bricklink.com/catalogItemInv.asp?S={set_number}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for inventory table
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    if len(rows) > 1:  # Has header and data rows
                        inventory = []
                        for row in rows[1:]:  # Skip header
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 4:
                                part_number = cells[0].get_text(strip=True)
                                part_name = cells[1].get_text(strip=True)
                                color_name = cells[2].get_text(strip=True)
                                quantity_text = cells[3].get_text(strip=True)
                                
                                # Extract quantity
                                import re
                                quantity_match = re.search(r'(\d+)', quantity_text)
                                quantity = int(quantity_match.group(1)) if quantity_match else 0
                                
                                if quantity > 0 and part_number:  # Valid entry
                                    # Get part image URL from Rebrickable
                                    part_image_url = f"https://cdn.rebrickable.com/media/parts/ldraw/{part_number}.png"
                                    
                                    inventory.append({
                                        'part_number': part_number,
                                        'part_name': part_name,
                                        'color_id': get_color_id(color_name),
                                        'color_name': color_name,
                                        'quantity': quantity,
                                        'is_spare': 'spare' in quantity_text.lower(),
                                        'part_image_url': part_image_url
                                    })
                        
                        if inventory:
                            return {
                                'set_number': set_number,
                                'set_name': f'LEGO Set {set_number}',
                                'set_image': set_info['set_image'] if set_info else '',
                                'set_url': set_info['set_url'] if set_info else '',
                                'year': set_info['year'] if set_info else None,
                                'num_parts': set_info['num_parts'] if set_info else len(inventory),
                                'inventory': inventory
                            }
        except Exception as e:
            print(f"Alternative scraping failed: {e}")
        
        # Final fallback to enhanced mock data
        print(f"All methods failed, using mock data for set {set_number}")
        enhanced_mock_inventory = [
            {
                'part_number': '3001',
                'part_name': 'Brick 2 x 4',
                'color_id': 1,
                'color_name': 'White',
                'quantity': 12,
                'is_spare': False,
                'part_image_url': 'https://cdn.rebrickable.com/media/parts/ldraw/3001.png'
            },
            {
                'part_number': '3002',
                'part_name': 'Brick 2 x 3',
                'color_id': 4,
                'color_name': 'Red',
                'quantity': 8,
                'is_spare': False,
                'part_image_url': 'https://cdn.rebrickable.com/media/parts/ldraw/3002.png'
            },
            {
                'part_number': '3003',
                'part_name': 'Brick 2 x 2',
                'color_id': 1,
                'color_name': 'White',
                'quantity': 6,
                'is_spare': True,
                'part_image_url': 'https://cdn.rebrickable.com/media/parts/ldraw/3003.png'
            },
            {
                'part_number': '3004',
                'part_name': 'Brick 1 x 2',
                'color_id': 4,
                'color_name': 'Red',
                'quantity': 4,
                'is_spare': False,
                'part_image_url': 'https://cdn.rebrickable.com/media/parts/ldraw/3004.png'
            },
            {
                'part_number': '3005',
                'part_name': 'Brick 1 x 1',
                'color_id': 1,
                'color_name': 'White',
                'quantity': 2,
                'is_spare': True,
                'part_image_url': 'https://cdn.rebrickable.com/media/parts/ldraw/3005.png'
            }
        ]
        
        return {
            'set_number': set_number,
            'set_name': f'LEGO Set {set_number}',
            'set_image': set_info['set_image'] if set_info else '',
            'set_url': set_info['set_url'] if set_info else '',
            'year': set_info['year'] if set_info else None,
            'num_parts': set_info['num_parts'] if set_info else len(enhanced_mock_inventory),
            'inventory': enhanced_mock_inventory
        }
    except Exception as e:
        print(f"Error fetching set inventory: {e}")
        return None

def get_color_id(color_name):
    """Map color names to color IDs"""
    color_map = {
        'White': 1, 'Black': 0, 'Red': 4, 'Blue': 7, 'Yellow': 3,
        'Green': 2, 'Orange': 25, 'Purple': 24, 'Pink': 23,
        'Light Gray': 9, 'Dark Gray': 10, 'Brown': 6, 'Tan': 19,
        'Lime': 27, 'Light Blue': 11, 'Dark Blue': 8, 'Dark Green': 5,
        'Bright Red': 21, 'Bright Blue': 23, 'Bright Yellow': 24,
        'Bright Green': 25, 'Bright Orange': 26, 'Bright Purple': 27
    }
    return color_map.get(color_name, 0)

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

@app.route('/update_inventory', methods=['POST'])
@login_required_json
def update_inventory():
    data = request.json
    set_number = data.get('set_number')
    custom_display_name = data.get('instance_name', 'Default')
    
    # Find the owned set
    owned_set = OwnedSet.query.filter_by(
        user_id=current_user.user_id,
        set_number=set_number,
        custom_display_name=custom_display_name
    ).first()
    
    if not owned_set:
        return jsonify({'error': 'Owned set not found'}), 404
    
    # Check if this is a batch save operation
    if 'modifications' in data:
        modifications = data.get('modifications', {})
        
        # Clear existing modifications for this owned set
        OwnedSetInventory.query.filter_by(owned_set_id=owned_set.owned_set_id).delete()
        
        # Add new modifications
        for part_key, actual_quantity in modifications.items():
            if actual_quantity != 0:  # Only save non-zero modifications
                part_number, color_id = part_key.split('_')
                
                # Find the original inventory part
                original_inv = OriginalSetInventory.query.filter_by(
                    set_number=set_number,
                    part_number=part_number,
                    color_id=int(color_id)
                ).first()
                
                if original_inv:
                    owned_inv = OwnedSetInventory(
                        owned_set_id=owned_set.owned_set_id,
                        inventory_part_id=original_inv.inventory_part_id,
                        actual_quantity=actual_quantity
                    )
                    db.session.add(owned_inv)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Inventory saved successfully'})
    
    # Legacy single update (for backward compatibility)
    part_number = data.get('part_number')
    color_id = data.get('color_id')
    actual_quantity = data.get('quantity_change', 0)
    
    # Find the original inventory part
    original_inv = OriginalSetInventory.query.filter_by(
        set_number=set_number,
        part_number=part_number,
        color_id=color_id
    ).first()
    
    if not original_inv:
        return jsonify({'error': 'Original inventory part not found'}), 404
    
    # Find existing owned inventory entry
    owned_inv = OwnedSetInventory.query.filter_by(
        owned_set_id=owned_set.owned_set_id,
        inventory_part_id=original_inv.inventory_part_id
    ).first()
    
    if owned_inv:
        if actual_quantity == 0:
            db.session.delete(owned_inv)
        else:
            owned_inv.actual_quantity = actual_quantity
    else:
        if actual_quantity != 0:
            owned_inv = OwnedSetInventory(
                owned_set_id=owned_set.owned_set_id,
                inventory_part_id=original_inv.inventory_part_id,
                actual_quantity=actual_quantity
            )
            db.session.add(owned_inv)
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/get_modified_inventory/<set_number>')
@login_required_json
def get_modified_inventory(set_number):
    custom_display_name = request.args.get('instance_name', 'Default')
    
    # Find the owned set
    owned_set = OwnedSet.query.filter_by(
        user_id=current_user.user_id,
        set_number=set_number,
        custom_display_name=custom_display_name
    ).first()
    
    if not owned_set:
        return jsonify({})
    
    owned_inventories = OwnedSetInventory.query.filter_by(
        owned_set_id=owned_set.owned_set_id
    ).all()
    
    result = {}
    for inv in owned_inventories:
        # Get the original inventory part to build the key
        original_inv = inv.original_inventory
        key = f"{original_inv.part_number}_{original_inv.color_id}"
        result[key] = inv.actual_quantity
    
    return jsonify(result)

@app.route('/my_collection')
@login_required
def my_collection():
    user_sets = OwnedSet.query.filter_by(user_id=current_user.user_id).order_by(OwnedSet.added_at.desc()).all()
    return render_template('my_collection.html', user_sets=user_sets)

@app.route('/add_to_collection', methods=['POST'])
@login_required_json
def add_to_collection():
    data = request.json
    set_number = data.get('set_number')
    set_name = data.get('set_name')
    custom_display_name = data.get('instance_name', 'Default')
    
    if not set_number or not set_name:
        return jsonify({'error': 'Set number and name are required'}), 400
    
    # Check if this exact instance already exists
    existing = OwnedSet.query.filter_by(
        user_id=current_user.user_id,
        set_number=set_number,
        custom_display_name=custom_display_name
    ).first()
    
    if existing:
        return jsonify({'error': 'This set instance already exists in your collection'}), 400
    
    # Add to collection
    new_set = OwnedSet(
        user_id=current_user.user_id,
        set_number=set_number,
        custom_display_name=custom_display_name
    )
    db.session.add(new_set)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Set added to collection successfully',
        'owned_set_id': new_set.owned_set_id
    })

@app.route('/remove_from_collection', methods=['POST'])
@login_required_json
def remove_from_collection():
    data = request.json
    owned_set_id = data.get('owned_set_id')
    
    if not owned_set_id:
        return jsonify({'error': 'Collection ID is required'}), 400
    
    collection_item = OwnedSet.query.filter_by(
        owned_set_id=owned_set_id,
        user_id=current_user.user_id
    ).first()
    
    if not collection_item:
        return jsonify({'error': 'Set not found in your collection'}), 404
    
    db.session.delete(collection_item)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Set removed from collection successfully'})

@app.route('/get_user_sets/<set_number>')
@login_required_json
def get_user_sets(set_number):
    user_sets = OwnedSet.query.filter_by(
        user_id=current_user.user_id,
        set_number=set_number
    ).all()
    
    result = []
    for user_set in user_sets:
        result.append({
            'id': user_set.owned_set_id,
            'set_number': user_set.set_number,
            # 'set_name': user_set.set.set_name if user_set.set else 'Unknown Set',
            'instance_name': user_set.custom_display_name,
            'added_at': user_set.added_at.isoformat()
        })
    
    return jsonify(result)

@app.route('/delete_set_instance', methods=['POST'])
@login_required_json
def delete_set_instance():
    data = request.json
    owned_set_id = data.get('owned_set_id')
    
    if not owned_set_id:
        return jsonify({'error': 'Collection ID is required'}), 400
    
    # Find the set instance
    user_set = OwnedSet.query.filter_by(
        owned_set_id=owned_set_id,
        user_id=current_user.user_id
    ).first()
    
    if not user_set:
        return jsonify({'error': 'Set instance not found'}), 404
    
    # Delete all inventory modifications for this instance
    OwnedSetInventory.query.filter_by(owned_set_id=user_set.owned_set_id).delete()
    
    # Delete the set instance
    db.session.delete(user_set)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Set instance deleted successfully'})

@app.route('/view_instance_inventory', methods=['POST'])
@login_required_json
def view_instance_inventory():
    data = request.json
    set_number = data.get('set_number')
    custom_display_name = data.get('instance_name', 'Default')
    
    if not set_number:
        return jsonify({'error': 'Set number is required'}), 400
    
    # Get inventory data
    inventory_data = get_set_inventory(set_number)
    
    if inventory_data:
        # Get original inventory from database
        original_inventory = get_original_inventory(set_number)
        
        # Add instance information and original inventory to the response
        inventory_data['instance_name'] = custom_display_name
        inventory_data['original_inventory'] = original_inventory
        return jsonify(inventory_data)
    else:
        return jsonify({'error': 'Failed to fetch set inventory'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

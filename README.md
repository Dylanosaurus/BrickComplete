# BrickComplete - LEGO Set Inventory Manager

A web application that allows you to search for LEGO sets using the Bricklink API and manage your personal inventory modifications.

## Features

- 🔍 Search LEGO sets by set number
- 📦 View complete set inventory with part details
- ➕➖ Modify inventory quantities with plus/minus buttons
- 🚫 **Prevents negative quantities** - Cannot reduce below zero
- 👤 User account system for saving modifications
- 💾 Automatic saving of inventory changes
- 📱 Responsive design for mobile and desktop
- 🔐 Bricklink API integration ready (credentials configured)

## Setup Instructions

### 1. Install Dependencies

Make sure you have Python 3.13 installed, then install the required packages:

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

1. Copy `env_example.txt` to `.env`
2. Edit `.env` and add your configuration:
   - `SECRET_KEY`: A random secret key for Flask sessions
   - `BRICKLINK_TOKEN`: Your Bricklink API token
   - `BRICKLINK_SECRET`: Your Bricklink API secret

### 3. Bricklink API Setup

1. Go to [Bricklink API Registration](https://www.bricklink.com/v2/api/register_consumer.page)
2. Register for API access
3. Get your token and secret
4. Add them to your `.env` file

### 4. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Usage

1. **Register/Login**: Create an account or login to save your inventory modifications
2. **Search Sets**: Enter a LEGO set number (e.g., "10265") to view its inventory
3. **Modify Inventory**: Use the + and - buttons to adjust quantities for your collection
4. **Auto-Save**: All changes are automatically saved to your account

## Current Status

⚠️ **Note**: The application currently uses mock data for demonstration purposes. To use real Bricklink API data, you'll need to:

1. Obtain Bricklink API credentials
2. Implement proper OAuth authentication
3. Update the API calls in `app.py` to use real endpoints

## Project Structure

```
BrickComplete/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── env_example.txt        # Environment variables template
├── .gitignore            # Git ignore file
├── README.md             # This file
├── instance/             # Database and instance files
│   ├── .gitkeep         # Keeps directory in git
│   └── brickcomplete.db # SQLite database (created automatically)
├── static/               # Static files (CSS, JS, images)
│   └── .gitkeep         # Keeps directory in git
└── templates/            # HTML templates
    ├── base.html         # Base template
    ├── index.html        # Main page
    ├── login.html        # Login page
    ├── my_collection.html # Collection page
    └── register.html     # Registration page
```

## Technologies Used

- **Backend**: Flask, SQLAlchemy, Flask-Login
- **Frontend**: Bootstrap 5, Font Awesome, Vanilla JavaScript
- **Database**: SQLite
- **API**: Bricklink API (when configured)

## Future Enhancements

- Real Bricklink API integration
- Part images and detailed information
- Export functionality for modified inventories
- Set comparison features
- Advanced search and filtering

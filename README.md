# BrickComplete - LEGO Set Inventory Manager

A comprehensive web application for LEGO enthusiasts to search, browse, and manage their LEGO set inventories with custom modifications. Built with a local SQLite database containing over 20,000 LEGO sets and their complete part inventories.

## Features

- 🔍 **Search & Browse**: Search LEGO sets by set number with autocomplete suggestions
- 📦 **Complete Inventories**: View detailed set inventories with part images, colors, and specifications
- ➕➖ **Custom Modifications**: Modify inventory quantities with intuitive plus/minus controls
- 🚫 **Smart Validation**: Prevents negative quantities and validates user inputs
- 👤 **User Accounts**: Secure user registration and authentication system
- 💾 **Auto-Save**: All inventory modifications are automatically saved to your account
- 📱 **Responsive Design**: Optimized for both desktop and mobile devices
- 🏗️ **Building Instructions**: Access to LEGO building instructions with image galleries
- 🎯 **Multiple Instances**: Create and manage multiple inventory instances per set
- 🔧 **Part Management**: Track spare parts and minifigure components separately

## Database

The application uses a comprehensive local SQLite database containing:
- **20,000+ LEGO sets** with complete metadata
- **15,000+ unique parts** with detailed specifications
- **1,000+ colors** with RGB values and transparency information
- **Complete inventories** for all sets including minifigure parts
- **Part categories** and relationships
- **Theme information** and hierarchies

## Setup Instructions

### 1. Install Dependencies

Make sure you have Python 3.8+ installed, then install the required packages:

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

1. Copy `env_example.txt` to `.env`
2. Edit `.env` and add your configuration:
   - `SECRET_KEY`: A random secret key for Flask sessions (generate a secure random string)

### 3. Database Setup

The application includes a pre-built database with LEGO data. If you need to rebuild the database:

```bash
python build_database.py
```

This will process the CSV files in the `instance/` directory and create the SQLite database.

### 4. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Usage

1. **Register/Login**: Create an account or login to save your inventory modifications
2. **Search Sets**: Enter a LEGO set number (e.g., "10265") to view its complete inventory
3. **Modify Inventory**: Use the + and - buttons to adjust quantities for your collection
4. **Create Instances**: Save multiple versions of the same set with different modifications
5. **View Instructions**: Access building instructions and part images
6. **Manage Collection**: View and organize all your modified sets in "My Collection"

## Project Structure

```
BrickComplete/
├── app.py                 # Main Flask application
├── database_service.py    # Database service layer
├── build_database.py      # Database builder from CSV files
├── requirements.txt       # Python dependencies
├── env_example.txt        # Environment variables template
├── README.md             # This file
├── instance/             # Database and data files
│   ├── lego_data.db      # Main LEGO database (SQLite)
│   ├── brickcomplete.db  # User data database (SQLite)
│   ├── sets.csv          # LEGO sets data
│   ├── parts.csv         # LEGO parts data
│   ├── colors.csv        # LEGO colors data
│   ├── inventories.csv   # Set inventories
│   ├── inventory_parts.csv # Part details
│   ├── inventory_minifigs.csv # Minifigure data
│   ├── minifigs.csv      # Minifigure information
│   ├── themes.csv        # LEGO themes
│   ├── part_categories.csv # Part categories
│   ├── part_relationships.csv # Part relationships
│   └── elements.csv      # Part elements with images
├── static/               # Static files (CSS, JS, images)
│   └── js/              # JavaScript files
│       ├── common.js    # Common JavaScript functions
│       └── lightbox.js  # Image lightbox functionality
└── templates/            # HTML templates
    ├── base.html         # Base template
    ├── index.html        # Main search page
    ├── login.html        # Login page
    ├── register.html     # Registration page
    └── my_collection.html # User collection page
```

## Technologies Used

- **Backend**: Python, Flask, SQLAlchemy, Flask-Login, Flask-WTF
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript (ES6), Font Awesome
- **Database**: SQLite with comprehensive LEGO data
- **Data Processing**: CSV processing, data normalization, and database optimization
- **Web Scraping**: BeautifulSoup4 for building instructions
- **Security**: WTForms validation, secure session management

## Key Features in Detail

### Database Architecture
- **Normalized Design**: Properly structured database with foreign key relationships
- **Efficient Queries**: Optimized for fast retrieval of complex set inventories
- **Data Integrity**: Comprehensive validation and constraint enforcement

### User Experience
- **Real-time Updates**: AJAX-powered interface for seamless interactions
- **Responsive Design**: Mobile-first approach with Bootstrap 5
- **Intuitive Controls**: Easy-to-use quantity modification system
- **Visual Feedback**: Part images, color swatches, and clear status indicators

### Data Management
- **Complete Inventories**: Every set includes all parts, colors, and quantities
- **Minifigure Support**: Separate tracking for minifigure parts and accessories
- **Spare Parts**: Identification and management of spare parts
- **Part Images**: High-quality part images from official LEGO sources

## Future Enhancements

- Export functionality for modified inventories (CSV, PDF)
- Set comparison features and analytics
- Advanced search and filtering options
- Community sharing of custom inventories
- Integration with LEGO building instructions API
- Mobile app development
- Advanced part tracking and wishlist features

## Contributing

This project demonstrates full-stack web development with a focus on:
- Database design and optimization
- User interface and experience design
- Data processing and normalization
- API design and RESTful endpoints
- Security and validation best practices

## License

This project is for educational and personal use. LEGO is a trademark of the LEGO Group.
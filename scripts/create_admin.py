#!/usr/bin/env python3
"""
Admin user creation utility for AI Job Assistant.

Creates an admin user account for system administration.

Usage:
    python scripts/create_admin.py                      # Interactive mode
    python scripts/create_admin.py --email admin@example.com --password secret
"""

import argparse
import getpass
import os
import sys
import re

# Add the backend directory to the path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

import bcrypt
from flask import Flask

from src.models.base import db
from src.models.user import User
from src.models.profile import Profile


def create_app():
    """Create Flask app for database access."""
    app = Flask(__name__)
    
    # Load configuration from environment
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/jobassistant'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    return True, ""


def create_admin(email: str, password: str, name: str = "Administrator"):
    """
    Create an admin user.
    
    Args:
        email: Admin email address
        password: Admin password (will be hashed)
        name: Admin display name
        
    Returns:
        Created User object or None if failed
    """
    # Check if user already exists
    existing = User.query.filter_by(email=email).first()
    if existing:
        print(f"❌ User with email '{email}' already exists")
        return None
    
    # Create user
    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name,
        is_active=True
    )
    db.session.add(user)
    db.session.flush()
    
    # Create basic profile
    profile = Profile(
        user_id=user.id,
        summary="Admin account for AI Job Assistant",
        preferences_json={
            'is_admin': True,
            'theme': 'system',
            'notifications_enabled': True
        }
    )
    db.session.add(profile)
    db.session.commit()
    
    return user


def main():
    parser = argparse.ArgumentParser(
        description='Create an admin user for AI Job Assistant',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_admin.py                                    Interactive mode
  python create_admin.py --email admin@company.com          Specify email only
  python create_admin.py -e admin@co.com -p SecurePass123   Non-interactive
        """
    )
    
    parser.add_argument(
        '-e', '--email',
        type=str,
        help='Admin email address'
    )
    parser.add_argument(
        '-p', '--password',
        type=str,
        help='Admin password (min 8 chars, mixed case, with digit)'
    )
    parser.add_argument(
        '-n', '--name',
        type=str,
        default='Administrator',
        help='Admin display name (default: Administrator)'
    )
    
    args = parser.parse_args()
    
    # Interactive mode for missing values
    email = args.email
    password = args.password
    name = args.name
    
    print("\n🔐 AI Job Assistant - Admin User Creation")
    print("=" * 50)
    
    # Get email
    if not email:
        while True:
            email = input("\nEmail: ").strip()
            if validate_email(email):
                break
            print("❌ Invalid email format. Please try again.")
    
    # Get password
    if not password:
        while True:
            password = getpass.getpass("\nPassword: ")
            is_valid, error = validate_password(password)
            if not is_valid:
                print(f"❌ {error}")
                continue
            
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("❌ Passwords do not match. Please try again.")
                continue
            break
    else:
        is_valid, error = validate_password(password)
        if not is_valid:
            print(f"❌ {error}")
            sys.exit(1)
    
    # Get name if not provided
    if args.name == 'Administrator' and not args.email:
        name_input = input(f"\nDisplay name [{name}]: ").strip()
        if name_input:
            name = name_input
    
    app = create_app()
    
    with app.app_context():
        user = create_admin(email, password, name)
        
        if user:
            print(f"\n{'=' * 50}")
            print("✅ Admin user created successfully!")
            print(f"{'=' * 50}")
            print(f"\n  Email: {email}")
            print(f"  Name: {name}")
            print(f"  User ID: {user.id}")
            print(f"\n💡 You can now log in with these credentials.\n")
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()

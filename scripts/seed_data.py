#!/usr/bin/env python3
"""
Database seeding script for AI Job Assistant.

Creates realistic test data including jobs, users, profiles, and related entities.

Usage:
    python scripts/seed_data.py --jobs 100              # Seed 100 jobs
    python scripts/seed_data.py --users 10              # Seed 10 users with profiles
    python scripts/seed_data.py --all                   # Seed all data
    python scripts/seed_data.py --reset                 # Reset and reseed (dev only)
    python scripts/seed_data.py --seed 42 --jobs 100    # Reproducible data with seed
"""

import argparse
import os
import sys
from datetime import datetime

# Add the backend directory to the path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, scripts_dir)

import bcrypt
from flask import Flask

from src.models.base import db
from src.models.user import User
from src.models.profile import Profile, WorkExperience, Education, Skill
from src.models.job import JobOffer
from generators.job_generator import JobGenerator
from generators.user_generator import UserGenerator


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


def seed_jobs(count: int = 100, seed: int = None):
    """
    Seed job listings into the database.
    
    Args:
        count: Number of jobs to create
        seed: Random seed for reproducibility
    """
    print(f"\n{'='*60}")
    print(f"Seeding {count} job listings...")
    print(f"{'='*60}")
    
    generator = JobGenerator(seed=seed)
    jobs_data = generator.generate_jobs(count)
    
    created = 0
    skipped = 0
    
    for job_data in jobs_data:
        # Check if job with this external_id already exists
        existing = JobOffer.query.filter_by(external_id=job_data['external_id']).first()
        if existing:
            skipped += 1
            continue
        
        job = JobOffer(
            external_id=job_data['external_id'],
            title=job_data['title'],
            company=job_data['company'],
            location=job_data['location'],
            description=job_data['description'],
            requirements=job_data['requirements'],
            salary_min=job_data['salary_min'],
            salary_max=job_data['salary_max'],
            job_type=job_data['job_type'],
            external_url=job_data['external_url'],
            posted_date=job_data['posted_date'],
            is_active=job_data['is_active']
        )
        db.session.add(job)
        created += 1
    
    db.session.commit()
    
    print(f"✅ Created {created} job listings")
    if skipped > 0:
        print(f"⏭️  Skipped {skipped} existing jobs")
    
    # Print statistics
    print(f"\nJob Statistics:")
    print(f"  - Total jobs in database: {JobOffer.query.count()}")
    
    # Count by job type
    for job_type in ['full-time', 'remote', 'contract', 'part-time']:
        count = JobOffer.query.filter_by(job_type=job_type).count()
        print(f"  - {job_type}: {count}")


def seed_users(count: int = 10, seed: int = None):
    """
    Seed users with complete profiles into the database.
    
    Args:
        count: Number of users to create
        seed: Random seed for reproducibility
    """
    print(f"\n{'='*60}")
    print(f"Seeding {count} users with profiles...")
    print(f"{'='*60}")
    
    generator = UserGenerator(seed=seed)
    default_password = hash_password('TestPassword123!')
    
    created_users = 0
    created_profiles = 0
    created_experiences = 0
    created_education = 0
    created_skills = 0
    skipped = 0
    
    for i in range(count):
        email = f"testuser{i+1}@example.com"
        
        # Check if user exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            skipped += 1
            continue
        
        # Create user
        user_data = generator.generate_user(email=email)
        user = User(
            email=user_data['email'],
            password_hash=default_password,
            name=user_data['name'],
            is_active=True
        )
        db.session.add(user)
        db.session.flush()  # Get the user ID
        created_users += 1
        
        # Create profile
        profile_data = generator.generate_profile(user.id)
        profile = Profile(
            user_id=user.id,
            summary=profile_data['summary'],
            location=profile_data['location'],
            phone=profile_data['phone'],
            preferences_json=profile_data['preferences_json']
        )
        db.session.add(profile)
        db.session.flush()
        created_profiles += 1
        
        # Create work experiences
        experiences_data = generator.generate_work_experiences(profile.id)
        for exp_data in experiences_data:
            experience = WorkExperience(
                profile_id=profile.id,
                company=exp_data['company'],
                job_title=exp_data['job_title'],
                start_date=exp_data['start_date'],
                end_date=exp_data['end_date'],
                description=exp_data['description'],
            )
            db.session.add(experience)
            created_experiences += 1
        
        # Create education
        education_data = generator.generate_education(profile.id)
        for edu_data in education_data:
            education = Education(
                profile_id=profile.id,
                institution=edu_data['institution'],
                degree=edu_data['degree'],
                field_of_study=edu_data['field_of_study'],
                start_date=edu_data['start_date'],
                end_date=edu_data['end_date'],
            )
            db.session.add(education)
            created_education += 1
        
        # Create skills
        skills_data = generator.generate_skills(profile.id)
        for skill_data in skills_data:
            skill = Skill(
                profile_id=profile.id,
                name=skill_data['name'],
                proficiency_level=skill_data['proficiency_level'],
            )
            db.session.add(skill)
            created_skills += 1
    
    db.session.commit()
    
    print(f"✅ Created {created_users} users")
    print(f"✅ Created {created_profiles} profiles")
    print(f"✅ Created {created_experiences} work experiences")
    print(f"✅ Created {created_education} education entries")
    print(f"✅ Created {created_skills} skills")
    if skipped > 0:
        print(f"⏭️  Skipped {skipped} existing users")
    
    print(f"\nTest User Credentials:")
    print(f"  - Email: testuser1@example.com (through testuser{count}@example.com)")
    print(f"  - Password: TestPassword123!")


def reset_database():
    """
    Reset the database by deleting all seeded data.
    WARNING: This is destructive and should only be used in development.
    """
    print(f"\n{'='*60}")
    print("⚠️  RESETTING DATABASE...")
    print(f"{'='*60}")
    
    # Delete in order due to foreign key constraints
    Skill.query.delete()
    Education.query.delete()
    WorkExperience.query.delete()
    Profile.query.delete()
    
    # Delete jobs
    JobOffer.query.delete()
    
    # Delete users (except admin)
    User.query.filter(User.email != 'admin@jobassistant.local').delete()
    
    db.session.commit()
    
    print("✅ Database reset complete (admin user preserved)")


def main():
    parser = argparse.ArgumentParser(
        description='Seed the database with test data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python seed_data.py --jobs 100              Create 100 job listings
  python seed_data.py --users 10              Create 10 test users with profiles
  python seed_data.py --all                   Create all test data
  python seed_data.py --seed 42 --jobs 100    Reproducible data generation
  python seed_data.py --reset --all           Reset and reseed everything
        """
    )
    
    parser.add_argument(
        '--jobs', 
        type=int, 
        metavar='N',
        help='Number of job listings to create'
    )
    parser.add_argument(
        '--users', 
        type=int, 
        metavar='N',
        help='Number of users to create (with profiles, experience, education, skills)'
    )
    parser.add_argument(
        '--all', 
        action='store_true',
        help='Seed all data (100 jobs, 10 users)'
    )
    parser.add_argument(
        '--reset', 
        action='store_true',
        help='Reset database before seeding (development only)'
    )
    parser.add_argument(
        '--seed', 
        type=int,
        metavar='N',
        help='Random seed for reproducible data generation'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.jobs, args.users, args.all, args.reset]):
        parser.print_help()
        sys.exit(1)
    
    app = create_app()
    
    with app.app_context():
        print(f"\n🌱 AI Job Assistant - Database Seeder")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if args.reset:
            confirm = input("\n⚠️  This will delete all seeded data. Continue? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Aborted.")
                sys.exit(0)
            reset_database()
        
        if args.all:
            seed_jobs(count=100, seed=args.seed)
            seed_users(count=10, seed=args.seed)
        else:
            if args.jobs:
                seed_jobs(count=args.jobs, seed=args.seed)
            if args.users:
                seed_users(count=args.users, seed=args.seed)
        
        print(f"\n{'='*60}")
        print("✅ Seeding complete!")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    main()

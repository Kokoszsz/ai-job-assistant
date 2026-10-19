"""
User and profile data generator for creating realistic test users.
"""

import random
from datetime import datetime, timedelta
from typing import Optional
from faker import Faker


class UserGenerator:
    """
    Generates realistic user and profile data for database seeding.
    
    Features:
    - Complete user profiles with work experience
    - Education history with realistic institutions
    - Skills with proficiency levels
    - Preferences and career goals
    """
    
    # Degree types and fields
    DEGREES = [
        ('Bachelor of Science', 'Computer Science'),
        ('Bachelor of Science', 'Information Technology'),
        ('Bachelor of Science', 'Data Science'),
        ('Bachelor of Arts', 'Business Administration'),
        ('Bachelor of Science', 'Engineering'),
        ('Bachelor of Arts', 'Marketing'),
        ('Bachelor of Science', 'Finance'),
        ('Master of Science', 'Computer Science'),
        ('Master of Business Administration', 'MBA'),
        ('Master of Science', 'Data Analytics'),
        ('Master of Science', 'Information Systems'),
        ('Bachelor of Arts', 'Communications'),
        ('Bachelor of Science', 'Mathematics'),
        ('Master of Arts', 'Human Resources'),
        ('Bachelor of Science', 'Accounting'),
    ]
    
    # Universities
    UNIVERSITIES = [
        'Stanford University', 'MIT', 'UC Berkeley', 'Carnegie Mellon University',
        'University of Michigan', 'Georgia Tech', 'University of Texas at Austin',
        'University of Washington', 'UCLA', 'Columbia University', 'NYU',
        'University of Illinois', 'Cornell University', 'Penn State University',
        'University of Florida', 'Ohio State University', 'University of Wisconsin',
        'Arizona State University', 'Boston University', 'Northwestern University'
    ]
    
    # Common skills by category
    SKILL_CATEGORIES = {
        'programming': [
            ('Python', 'advanced'), ('JavaScript', 'advanced'), ('TypeScript', 'intermediate'),
            ('Java', 'intermediate'), ('C++', 'beginner'), ('Go', 'beginner'),
            ('Ruby', 'intermediate'), ('PHP', 'beginner'), ('Swift', 'beginner'),
            ('Rust', 'beginner'), ('Kotlin', 'intermediate'), ('C#', 'intermediate')
        ],
        'frameworks': [
            ('React', 'advanced'), ('Node.js', 'advanced'), ('Django', 'intermediate'),
            ('Flask', 'intermediate'), ('Spring Boot', 'beginner'), ('Angular', 'beginner'),
            ('Vue.js', 'intermediate'), ('FastAPI', 'intermediate'), ('Express.js', 'advanced'),
            ('Next.js', 'intermediate'), ('Rails', 'beginner')
        ],
        'data': [
            ('SQL', 'advanced'), ('PostgreSQL', 'advanced'), ('MongoDB', 'intermediate'),
            ('Redis', 'intermediate'), ('Elasticsearch', 'beginner'), ('MySQL', 'advanced'),
            ('Pandas', 'intermediate'), ('NumPy', 'intermediate'), ('Spark', 'beginner')
        ],
        'cloud': [
            ('AWS', 'intermediate'), ('Docker', 'advanced'), ('Kubernetes', 'beginner'),
            ('Azure', 'beginner'), ('GCP', 'beginner'), ('Terraform', 'beginner'),
            ('CI/CD', 'intermediate'), ('Linux', 'advanced'), ('Git', 'advanced')
        ],
        'soft_skills': [
            ('Communication', 'advanced'), ('Leadership', 'intermediate'),
            ('Problem Solving', 'advanced'), ('Team Collaboration', 'advanced'),
            ('Project Management', 'intermediate'), ('Agile/Scrum', 'intermediate'),
            ('Time Management', 'advanced'), ('Critical Thinking', 'advanced')
        ]
    }
    
    # Job titles for work experience
    JOB_TITLES = [
        'Software Engineer', 'Junior Developer', 'Senior Developer', 'Full Stack Developer',
        'Frontend Developer', 'Backend Developer', 'Data Analyst', 'Product Manager',
        'DevOps Engineer', 'QA Engineer', 'Technical Lead', 'Engineering Manager',
        'Solutions Architect', 'Data Scientist', 'ML Engineer', 'Cloud Engineer'
    ]
    
    # Companies for work experience
    COMPANIES = [
        'Google', 'Amazon', 'Microsoft', 'Apple', 'Meta', 'Netflix', 'Uber', 'Airbnb',
        'Salesforce', 'Adobe', 'Oracle', 'IBM', 'Cisco', 'Intel', 'VMware',
        'Stripe', 'Square', 'Shopify', 'Twilio', 'Datadog', 'Snowflake',
        'Acme Corp', 'TechStart Inc', 'DataFlow Systems', 'CloudNine Solutions',
        'InnovateTech', 'Digital Dynamics', 'CodeCraft LLC', 'ByteWorks'
    ]
    
    # Locations
    LOCATIONS = [
        'San Francisco, CA', 'New York, NY', 'Seattle, WA', 'Austin, TX',
        'Boston, MA', 'Denver, CO', 'Chicago, IL', 'Los Angeles, CA',
        'Atlanta, GA', 'Portland, OR', 'Remote'
    ]
    
    # Preferred job types
    JOB_TYPE_PREFERENCES = ['full-time', 'remote', 'contract', 'part-time']
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the user generator.
        
        Args:
            seed: Random seed for reproducible data generation
        """
        self.faker = Faker()
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)
    
    def generate_user(self, email: Optional[str] = None) -> dict:
        """
        Generate a user account.
        
        Args:
            email: Optional email. If not provided, generates one.
            
        Returns:
            Dictionary with user data
        """
        first_name = self.faker.first_name()
        last_name = self.faker.last_name()
        
        if email is None:
            email = f"{first_name.lower()}.{last_name.lower()}@{self.faker.free_email_domain()}"
        
        return {
            'email': email,
            'password_hash': 'placeholder_will_be_hashed',  # Will be properly hashed in seed script
            'name': f"{first_name} {last_name}",
            'is_active': True,
        }
    
    def generate_profile(self, user_id: str) -> dict:
        """
        Generate a user profile.
        
        Args:
            user_id: UUID of the associated user
            
        Returns:
            Dictionary with profile data
        """
        preferred_locations = random.sample(self.LOCATIONS, random.randint(1, 4))
        preferred_job_types = random.sample(self.JOB_TYPE_PREFERENCES, random.randint(1, 3))
        
        return {
            'user_id': user_id,
            'summary': self.faker.paragraph(nb_sentences=5),
            'location': random.choice(self.LOCATIONS),
            'phone': self.faker.phone_number(),
            'preferences_json': {
                'preferred_locations': preferred_locations,
                'preferred_job_types': preferred_job_types,
                'salary_expectation_min': random.choice([60000, 80000, 100000, 120000, 150000]),
                'salary_expectation_max': random.choice([100000, 130000, 160000, 200000, 250000]),
                'open_to_relocation': random.choice([True, False]),
                'remote_preference': random.choice(['remote_only', 'hybrid', 'on_site', 'flexible']),
            }
        }
    
    def generate_work_experiences(self, profile_id: str, count: int = None) -> list[dict]:
        """
        Generate work experience entries.
        
        Args:
            profile_id: UUID of the associated profile
            count: Number of work experiences (random 1-4 if not specified)
            
        Returns:
            List of work experience dictionaries
        """
        if count is None:
            count = random.randint(1, 4)
        
        experiences = []
        current_year = datetime.now().year
        end_date = None  # Most recent job is current
        
        for i in range(count):
            duration_years = random.randint(1, 4)
            
            if i == 0:
                # Current job
                start_date = datetime(current_year - duration_years, random.randint(1, 12), 1)
                actual_end_date = None  # Current position
            else:
                # Previous jobs
                if end_date is None:
                    end_date = datetime(current_year, random.randint(1, 12), 1)
                
                start_date = datetime(end_date.year - duration_years, random.randint(1, 12), 1)
                actual_end_date = end_date
                end_date = start_date  # For next iteration
            
            experiences.append({
                'profile_id': profile_id,
                'company': random.choice(self.COMPANIES),
                'job_title': self.JOB_TITLES[min(i, len(self.JOB_TITLES) - 1)],  # More senior titles first
                'start_date': start_date.date(),
                'end_date': actual_end_date.date() if actual_end_date else None,
                'description': self.faker.paragraph(nb_sentences=4),
            })
        
        return experiences
    
    def generate_education(self, profile_id: str, count: int = None) -> list[dict]:
        """
        Generate education entries.
        
        Args:
            profile_id: UUID of the associated profile
            count: Number of education entries (random 1-2 if not specified)
            
        Returns:
            List of education dictionaries
        """
        if count is None:
            count = random.randint(1, 2)
        
        education_list = []
        graduation_year = datetime.now().year - random.randint(2, 15)
        
        for i in range(count):
            degree_type, field = random.choice(self.DEGREES)
            
            # Master's degrees come after bachelor's
            if i == 0 and 'Master' in degree_type:
                degree_type, field = random.choice([d for d in self.DEGREES if 'Bachelor' in d[0]])
            
            duration = 4 if 'Bachelor' in degree_type else 2
            start_year = graduation_year - duration
            
            education_list.append({
                'profile_id': profile_id,
                'institution': random.choice(self.UNIVERSITIES),
                'degree': degree_type,
                'field_of_study': field,
                'start_date': datetime(start_year, 9, 1).date(),  # Academic year starts in September
                'end_date': datetime(graduation_year, 5, 15).date(),  # Graduation in May
            })
            
            graduation_year = start_year - random.randint(0, 2)  # Gap for next degree
        
        return education_list
    
    def generate_skills(self, profile_id: str, count: int = None) -> list[dict]:
        """
        Generate skill entries.
        
        Args:
            profile_id: UUID of the associated profile
            count: Number of skills (random 8-15 if not specified)
            
        Returns:
            List of skill dictionaries
        """
        if count is None:
            count = random.randint(8, 15)
        
        # Get random skills from different categories
        all_skills = []
        for category, skills in self.SKILL_CATEGORIES.items():
            sample_size = min(random.randint(1, 4), len(skills))
            selected = random.sample(skills, sample_size)
            for skill_name, default_level in selected:
                # Randomize proficiency level a bit
                level = random.choice(['beginner', 'intermediate', 'advanced']) if random.random() > 0.6 else default_level
                all_skills.append({
                    'profile_id': profile_id,
                    'name': skill_name,
                    'proficiency_level': level,
                })
        
        return random.sample(all_skills, min(count, len(all_skills)))
    
    def generate_complete_user(self) -> dict:
        """
        Generate a complete user with profile, experience, education, and skills.
        
        Returns:
            Dictionary containing all user-related data
        """
        user = self.generate_user()
        
        return {
            'user': user,
            'profile': None,  # Will be created after user is inserted and we have user_id
            'work_experiences': [],
            'education': [],
            'skills': []
        }
    
    def generate_users(self, count: int = 10) -> list[dict]:
        """
        Generate multiple complete users.
        
        Args:
            count: Number of users to generate
            
        Returns:
            List of user data dictionaries
        """
        users = []
        for i in range(count):
            user_data = self.generate_user(email=f"testuser{i+1}@example.com")
            users.append(user_data)
        return users

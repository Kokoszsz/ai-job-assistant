"""
Job data generator for creating realistic job listings.
"""

import random
from datetime import datetime, timedelta
from typing import Optional
from faker import Faker


class JobGenerator:
    """
    Generates realistic job listing data for database seeding.
    
    Features:
    - 12 industries with industry-specific job titles
    - 4 experience levels (entry, mid, senior, lead)
    - 4 job types (full-time, remote, contract, part-time)
    - Realistic salary ranges by experience level
    - Diverse locations (US cities)
    - Detailed descriptions and requirements
    """
    
    # Industry definitions with job titles
    INDUSTRIES = {
        'technology': {
            'name': 'Technology',
            'titles': [
                'Software Engineer', 'Backend Developer', 'Frontend Developer',
                'Full Stack Developer', 'DevOps Engineer', 'Data Engineer',
                'Machine Learning Engineer', 'Cloud Architect', 'Site Reliability Engineer',
                'Mobile Developer', 'QA Engineer', 'Security Engineer'
            ],
            'skills': [
                'Python', 'JavaScript', 'TypeScript', 'React', 'Node.js', 'AWS',
                'Docker', 'Kubernetes', 'PostgreSQL', 'MongoDB', 'Git', 'CI/CD',
                'REST APIs', 'GraphQL', 'Microservices', 'Agile', 'Linux'
            ]
        },
        'finance': {
            'name': 'Finance & Banking',
            'titles': [
                'Financial Analyst', 'Investment Banker', 'Risk Analyst',
                'Portfolio Manager', 'Quantitative Analyst', 'Compliance Officer',
                'Financial Advisor', 'Credit Analyst', 'Actuary', 'Auditor'
            ],
            'skills': [
                'Financial Modeling', 'Excel', 'SQL', 'Bloomberg Terminal', 'Python',
                'Risk Management', 'Regulatory Compliance', 'Valuation', 'VBA',
                'Financial Reporting', 'CFA', 'Data Analysis'
            ]
        },
        'healthcare': {
            'name': 'Healthcare',
            'titles': [
                'Clinical Data Analyst', 'Healthcare Administrator', 'Medical Coder',
                'Health Informatics Specialist', 'Pharmacy Manager', 'Clinical Research Associate',
                'Healthcare Consultant', 'Medical Science Liaison', 'Patient Care Coordinator'
            ],
            'skills': [
                'HIPAA', 'EHR Systems', 'Medical Terminology', 'Clinical Trials',
                'Data Analysis', 'Healthcare Regulations', 'Epic', 'Cerner',
                'Patient Care', 'Quality Assurance', 'ICD-10', 'CPT Coding'
            ]
        },
        'retail': {
            'name': 'Retail & E-commerce',
            'titles': [
                'E-commerce Manager', 'Retail Operations Manager', 'Merchandising Analyst',
                'Supply Chain Coordinator', 'Category Manager', 'Store Manager',
                'Inventory Analyst', 'Customer Experience Manager', 'Buyer'
            ],
            'skills': [
                'Inventory Management', 'Shopify', 'Retail Analytics', 'Merchandising',
                'Supply Chain', 'Customer Service', 'POS Systems', 'SAP',
                'Demand Forecasting', 'Vendor Management', 'Sales Analysis'
            ]
        },
        'marketing': {
            'name': 'Marketing & Advertising',
            'titles': [
                'Digital Marketing Manager', 'Content Strategist', 'SEO Specialist',
                'Social Media Manager', 'Brand Manager', 'Marketing Analyst',
                'Growth Hacker', 'Product Marketing Manager', 'Email Marketing Specialist'
            ],
            'skills': [
                'Google Analytics', 'SEO', 'SEM', 'Content Marketing', 'Social Media',
                'HubSpot', 'Salesforce', 'A/B Testing', 'Copywriting', 'Marketing Automation',
                'PPC', 'Adobe Creative Suite', 'Data Analysis'
            ]
        },
        'consulting': {
            'name': 'Consulting',
            'titles': [
                'Management Consultant', 'Strategy Consultant', 'Business Analyst',
                'IT Consultant', 'Operations Consultant', 'HR Consultant',
                'Change Management Consultant', 'Process Improvement Specialist'
            ],
            'skills': [
                'Strategy', 'Problem Solving', 'PowerPoint', 'Excel', 'Data Analysis',
                'Project Management', 'Client Relations', 'Process Improvement',
                'Change Management', 'Stakeholder Management', 'Business Development'
            ]
        },
        'manufacturing': {
            'name': 'Manufacturing',
            'titles': [
                'Production Manager', 'Quality Control Engineer', 'Industrial Engineer',
                'Process Engineer', 'Manufacturing Engineer', 'Plant Manager',
                'Supply Chain Manager', 'Maintenance Manager', 'Operations Director'
            ],
            'skills': [
                'Lean Manufacturing', 'Six Sigma', 'Quality Control', 'CAD',
                'ERP Systems', 'Production Planning', 'Safety Compliance', 'ISO Standards',
                'Process Optimization', 'Inventory Control', 'Automation'
            ]
        },
        'education': {
            'name': 'Education',
            'titles': [
                'Instructional Designer', 'Curriculum Developer', 'Education Consultant',
                'Training Manager', 'Academic Advisor', 'Program Coordinator',
                'E-Learning Developer', 'Education Technology Specialist'
            ],
            'skills': [
                'Curriculum Development', 'LMS', 'Instructional Design', 'E-Learning',
                'Assessment Design', 'Training Delivery', 'Educational Technology',
                'Content Creation', 'Student Engagement', 'Program Management'
            ]
        },
        'media': {
            'name': 'Media & Entertainment',
            'titles': [
                'Content Producer', 'Video Editor', 'Creative Director',
                'Social Media Producer', 'Digital Content Manager', 'UX Designer',
                'Graphic Designer', 'Motion Graphics Designer', 'Art Director'
            ],
            'skills': [
                'Adobe Creative Suite', 'Video Production', 'Content Strategy',
                'Social Media', 'Storytelling', 'Brand Development', 'Photography',
                'Animation', 'UI/UX Design', 'Project Management'
            ]
        },
        'legal': {
            'name': 'Legal',
            'titles': [
                'Paralegal', 'Legal Assistant', 'Contracts Manager',
                'Compliance Analyst', 'Legal Operations Manager', 'Corporate Counsel',
                'Litigation Support Specialist', 'Legal Project Manager'
            ],
            'skills': [
                'Legal Research', 'Contract Review', 'Compliance', 'Litigation',
                'Document Management', 'Legal Writing', 'Regulatory Affairs',
                'Corporate Law', 'Intellectual Property', 'Due Diligence'
            ]
        },
        'hr': {
            'name': 'Human Resources',
            'titles': [
                'HR Manager', 'Recruiter', 'Talent Acquisition Specialist',
                'HR Business Partner', 'Compensation Analyst', 'Training Coordinator',
                'Employee Relations Specialist', 'HRIS Analyst', 'Benefits Administrator'
            ],
            'skills': [
                'Recruiting', 'Employee Relations', 'HRIS', 'Benefits Administration',
                'Performance Management', 'Onboarding', 'Talent Management',
                'Labor Law', 'Compensation', 'Workday', 'ADP'
            ]
        },
        'data_science': {
            'name': 'Data Science & Analytics',
            'titles': [
                'Data Scientist', 'Data Analyst', 'Business Intelligence Analyst',
                'Machine Learning Engineer', 'AI Research Scientist', 'Analytics Manager',
                'Data Architect', 'Statistician', 'NLP Engineer'
            ],
            'skills': [
                'Python', 'R', 'SQL', 'Machine Learning', 'Deep Learning', 'TensorFlow',
                'PyTorch', 'Tableau', 'Power BI', 'Statistics', 'Data Visualization',
                'Big Data', 'Spark', 'NLP', 'A/B Testing'
            ]
        }
    }
    
    # Experience levels with salary multipliers
    EXPERIENCE_LEVELS = {
        'entry': {
            'name': 'Entry Level',
            'years': '0-2 years',
            'prefix': 'Junior ',
            'salary_range': (50000, 75000)
        },
        'mid': {
            'name': 'Mid Level',
            'years': '3-5 years',
            'prefix': '',
            'salary_range': (75000, 110000)
        },
        'senior': {
            'name': 'Senior Level',
            'years': '6-10 years',
            'prefix': 'Senior ',
            'salary_range': (110000, 160000)
        },
        'lead': {
            'name': 'Lead/Principal',
            'years': '10+ years',
            'prefix': 'Lead ',
            'salary_range': (150000, 220000)
        }
    }
    
    # Job types
    JOB_TYPES = ['full-time', 'remote', 'contract', 'part-time']
    
    # US cities for job locations
    LOCATIONS = [
        'San Francisco, CA', 'New York, NY', 'Seattle, WA', 'Austin, TX',
        'Boston, MA', 'Denver, CO', 'Chicago, IL', 'Los Angeles, CA',
        'Atlanta, GA', 'Portland, OR', 'San Diego, CA', 'Miami, FL',
        'Washington, DC', 'Phoenix, AZ', 'Dallas, TX', 'Minneapolis, MN',
        'Philadelphia, PA', 'Nashville, TN', 'Raleigh, NC', 'Salt Lake City, UT'
    ]
    
    # Company name patterns
    COMPANY_SUFFIXES = [
        'Inc.', 'Corp.', 'LLC', 'Technologies', 'Solutions', 'Systems',
        'Group', 'Partners', 'Labs', 'Digital', 'Consulting', 'Services'
    ]
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the job generator.
        
        Args:
            seed: Random seed for reproducible data generation
        """
        self.faker = Faker()
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)
    
    def generate_company_name(self) -> str:
        """Generate a realistic company name."""
        patterns = [
            lambda: f"{self.faker.last_name()} {random.choice(self.COMPANY_SUFFIXES)}",
            lambda: f"{self.faker.last_name()} & {self.faker.last_name()}",
            lambda: f"{self.faker.word().title()}{random.choice(['Tech', 'Soft', 'Data', 'Cloud', 'Net'])}",
            lambda: f"{self.faker.word().title()} {random.choice(self.COMPANY_SUFFIXES)}",
            lambda: f"{self.faker.first_name()}{self.faker.last_name()} {random.choice(['Ventures', 'Capital', 'Holdings'])}",
        ]
        return random.choice(patterns)()
    
    def generate_description(self, industry: dict, title: str, level: dict) -> str:
        """Generate a realistic job description."""
        skills = random.sample(industry['skills'], min(6, len(industry['skills'])))
        
        description = f"""We are looking for a talented {title} to join our growing team.

About the Role:
{self.faker.paragraph(nb_sentences=3)}

What You'll Do:
• {self.faker.sentence()}
• {self.faker.sentence()}
• {self.faker.sentence()}
• {self.faker.sentence()}
• {self.faker.sentence()}

Requirements:
• {level['years']} of relevant experience
• Strong proficiency in {', '.join(skills[:3])}
• Experience with {', '.join(skills[3:])}
• Excellent communication and collaboration skills
• {self.faker.sentence()}

Nice to Have:
• {self.faker.sentence()}
• {self.faker.sentence()}

Benefits:
• Competitive salary and equity package
• Health, dental, and vision insurance
• Flexible PTO policy
• Remote work options
• Professional development budget
• 401(k) matching
"""
        return description.strip()
    
    def generate_requirements(self, industry: dict, level: dict) -> str:
        """Generate job requirements."""
        skills = random.sample(industry['skills'], min(5, len(industry['skills'])))
        
        requirements = f"""• {level['years']} of professional experience
• Proficiency in {', '.join(skills[:3])}
• Experience with {', '.join(skills[3:])}
• Strong problem-solving abilities
• Excellent verbal and written communication
• Bachelor's degree in related field or equivalent experience
• Ability to work independently and in a team environment"""
        
        return requirements.strip()
    
    def generate_job(self, external_id: Optional[str] = None) -> dict:
        """
        Generate a single job listing.
        
        Args:
            external_id: Optional external ID. If not provided, generates UUID-like string.
            
        Returns:
            Dictionary with job data ready for database insertion
        """
        # Select random industry and level
        industry_key = random.choice(list(self.INDUSTRIES.keys()))
        industry = self.INDUSTRIES[industry_key]
        
        level_key = random.choice(list(self.EXPERIENCE_LEVELS.keys()))
        level = self.EXPERIENCE_LEVELS[level_key]
        
        # Generate title with appropriate prefix
        base_title = random.choice(industry['titles'])
        if level_key == 'entry':
            title = f"Junior {base_title}"
        elif level_key == 'lead':
            title = f"Lead {base_title}" if 'Lead' not in base_title else f"Principal {base_title}"
        elif level_key == 'senior':
            title = f"Senior {base_title}" if 'Senior' not in base_title else base_title
        else:
            title = base_title
        
        # Generate salary range
        min_salary = random.randint(level['salary_range'][0], level['salary_range'][0] + 10000)
        max_salary = random.randint(level['salary_range'][1] - 10000, level['salary_range'][1])
        
        # Job type with weighted distribution
        job_type = random.choices(
            self.JOB_TYPES,
            weights=[50, 30, 15, 5],  # full-time most common
            k=1
        )[0]
        
        # Posted date (distributed over last 30 days)
        days_ago = random.randint(0, 30)
        posted_date = (datetime.utcnow() - timedelta(days=days_ago)).date()
        
        # Location (remote jobs can be "Remote" or "Remote - {city}")
        if job_type == 'remote':
            location = random.choice(['Remote', f"Remote - {random.choice(self.LOCATIONS)}"])
        else:
            location = random.choice(self.LOCATIONS)
        
        return {
            'external_id': external_id or f"job_{self.faker.uuid4()[:8]}",
            'title': title,
            'company': self.generate_company_name(),
            'location': location,
            'description': self.generate_description(industry, title, level),
            'requirements': self.generate_requirements(industry, level),
            'salary_min': min_salary,
            'salary_max': max_salary,
            'job_type': job_type,
            'external_url': f"https://jobs.example.com/{self.faker.uuid4()[:8]}",
            'posted_date': posted_date,
            'is_active': True,
        }
    
    def generate_jobs(self, count: int = 100) -> list[dict]:
        """
        Generate multiple job listings.
        
        Args:
            count: Number of jobs to generate
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        for i in range(count):
            job = self.generate_job(external_id=f"job_{i+1:04d}")
            jobs.append(job)
        return jobs

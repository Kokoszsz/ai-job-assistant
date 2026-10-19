"""
Database Tools
==============
Tool definitions for AI agents to query the database.
Provides function calling schemas for job search, profile queries, and CV generation.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DatabaseTools:
    """
    Provides database query tools for AI function calling.
    Agents use these tools to search jobs, fetch profiles, etc.
    """

    def __init__(self, db_session):
        """
        Initialize database tools.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    @staticmethod
    def get_tool_definitions() -> List[Dict[str, Any]]:
        """
        Get OpenAI function calling tool definitions.

        Returns:
            List of tool schemas for OpenAI API
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_jobs",
                    "description": "Search for jobs in the database based on keywords, location, and filters",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keywords": {
                                "type": "string",
                                "description": "Search keywords (job title, skills, technologies)",
                            },
                            "location": {
                                "type": "string",
                                "description": "Job location (city, state, or 'remote')",
                            },
                            "job_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Job types (full-time, part-time, contract, remote)",
                            },
                            "min_salary": {
                                "type": "number",
                                "description": "Minimum salary in USD",
                            },
                            "max_salary": {
                                "type": "number",
                                "description": "Maximum salary in USD",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 10)",
                                "default": 10,
                            },
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_job_details",
                    "description": "Get detailed information about a specific job",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "integer",
                                "description": "Job ID",
                            },
                        },
                        "required": ["job_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_user_profile",
                    "description": "Get user's profile including experience, education, and skills",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "integer",
                                "description": "User ID",
                            },
                        },
                        "required": ["user_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_cv",
                    "description": "Generate a professional CV for the user. Can create a generic CV or one tailored to a specific job.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "integer",
                                "description": "User ID to generate CV for",
                            },
                            "job_id": {
                                "type": "integer",
                                "description": "Optional job ID to tailor the CV for a specific position",
                            },
                            "title": {
                                "type": "string",
                                "description": "Optional title for the CV",
                            },
                        },
                        "required": ["user_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_user_cvs",
                    "description": "List all CVs the user has created",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "integer",
                                "description": "User ID",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of CVs to return (default: 10)",
                                "default": 10,
                            },
                        },
                        "required": ["user_id"],
                    },
                },
            },
        ]

    def search_jobs(
        self,
        keywords: Optional[str] = None,
        location: Optional[str] = None,
        job_types: Optional[List[str]] = None,
        min_salary: Optional[float] = None,
        max_salary: Optional[float] = None,
        limit: int = 10,
    ) -> str:
        """
        Search jobs in database.

        Returns:
            JSON string with search results
        """
        try:
            from ...models.job import JobOffer

            # Start with active jobs only
            query = self.db.query(JobOffer).filter(JobOffer.is_active == True)

            # Apply filters
            if keywords:
                search_term = f"%{keywords}%"
                query = query.filter(
                    (JobOffer.title.ilike(search_term))
                    | (JobOffer.description.ilike(search_term))
                    | (JobOffer.requirements.ilike(search_term))
                )

            if location:
                query = query.filter(JobOffer.location.ilike(f"%{location}%"))

            if job_types:
                query = query.filter(JobOffer.job_type.in_(job_types))

            if min_salary is not None:
                query = query.filter(JobOffer.salary_min >= min_salary)

            if max_salary is not None:
                query = query.filter(JobOffer.salary_max <= max_salary)

            # Execute query
            jobs = query.limit(limit).all()

            # Format results
            results = []
            for job in jobs:
                results.append(
                    {
                        "id": job.id,
                        "title": job.title,
                        "company": job.company,
                        "location": job.location,
                        "job_type": job.job_type,
                        "salary_min": job.salary_min,
                        "salary_max": job.salary_max,
                        "category": job.category,
                        "tags": job.tags,
                        "description": job.description[:200] + "..." if len(job.description) > 200 else job.description,
                        "posted_date": job.posted_date.isoformat() if job.posted_date else None,
                    }
                )

            return json.dumps(
                {
                    "success": True,
                    "count": len(results),
                    "jobs": results,
                }
            )

        except Exception as e:
            logger.error(f"Error searching jobs: {e}", exc_info=True)
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    def get_job_details(self, job_id: int) -> str:
        """
        Get detailed job information.

        Returns:
            JSON string with job details
        """
        try:
            from ...models.job import JobOffer

            job = self.db.query(JobOffer).filter(JobOffer.id == job_id).first()

            if not job:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Job {job_id} not found",
                    }
                )

            return json.dumps(
                {
                    "success": True,
                    "job": {
                        "id": job.id,
                        "title": job.title,
                        "company": job.company,
                        "location": job.location,
                        "job_type": job.job_type,
                        "salary_min": job.salary_min,
                        "salary_max": job.salary_max,
                        "description": job.description,
                        "requirements": job.requirements,
                        "category": job.category,
                        "tags": job.tags,
                        "company_logo_url": job.company_logo_url,
                        "posted_date": job.posted_date.isoformat() if job.posted_date else None,
                        "external_url": job.external_url,
                    },
                }
            )

        except Exception as e:
            logger.error(f"Error getting job details: {e}", exc_info=True)
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    def get_user_profile(self, user_id: int) -> str:
        """
        Get user profile with experience and skills.

        Returns:
            JSON string with profile data
        """
        try:
            from ...models.profile import Profile
            from ...models.user import User

            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.profile:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Profile for user {user_id} not found",
                    }
                )

            profile = user.profile

            # Format work experience
            experiences = []
            for exp in profile.work_experiences:
                experiences.append(
                    {
                        "job_title": exp.job_title,
                        "company": exp.company,
                        "location": exp.location,
                        "start_date": exp.start_date.isoformat() if exp.start_date else None,
                        "end_date": exp.end_date.isoformat() if exp.end_date else None,
                        "description": exp.description,
                    }
                )

            # Format education
            education = []
            for edu in profile.education:
                education.append(
                    {
                        "degree": edu.degree,
                        "field_of_study": edu.field_of_study,
                        "institution": edu.institution,
                        "graduation_date": edu.graduation_date.isoformat() if edu.graduation_date else None,
                    }
                )

            # Format skills
            skills = [skill.name for skill in profile.skills]

            return json.dumps(
                {
                    "success": True,
                    "profile": {
                        "name": user.name,
                        "email": user.email,
                        "summary": profile.summary,
                        "location": profile.location,
                        "phone": profile.phone,
                        "job_preferences": {
                            "preferred_locations": profile.preferred_locations or [],
                            "preferred_job_types": profile.preferred_job_types or [],
                            "min_salary": profile.min_salary,
                            "max_salary": profile.max_salary,
                        },
                        "work_experiences": experiences,
                        "education": education,
                        "skills": skills,
                    },
                }
            )

        except Exception as e:
            logger.error(f"Error getting user profile: {e}", exc_info=True)
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    def generate_cv(
        self,
        user_id: int,
        job_id: Optional[int] = None,
        title: Optional[str] = None,
    ) -> str:
        """
        Generate a CV for the user, optionally tailored to a specific job.

        Args:
            user_id: User ID to generate CV for
            job_id: Optional job ID to tailor the CV for
            title: Optional title for the CV

        Returns:
            JSON string with generated CV info
        """
        try:
            from ...services.cv_service import CVService

            if job_id:
                # Generate tailored CV
                cv = CVService.generate_tailored_cv(
                    user_id=user_id,
                    job_offer_id=job_id,
                    title=title,
                )
            else:
                # Generate generic CV
                cv = CVService.generate_generic_cv(
                    user_id=user_id,
                    title=title,
                )

            return json.dumps(
                {
                    "success": True,
                    "message": "CV generated successfully",
                    "cv": {
                        "id": cv["id"],
                        "title": cv["title"],
                        "is_ai_generated": cv["is_ai_generated"],
                        "target_position": cv.get("target_position"),
                        "created_at": cv["created_at"],
                        "job_offer": cv.get("job_offer"),
                    },
                }
            )

        except ValueError as e:
            logger.warning(f"CV generation validation error: {str(e)}")
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )
        except Exception as e:
            logger.error(f"Error generating CV: {e}", exc_info=True)
            return json.dumps(
                {
                    "success": False,
                    "error": f"Failed to generate CV: {str(e)}",
                }
            )

    def list_user_cvs(self, user_id: int, limit: int = 10) -> str:
        """
        List user's CVs.

        Args:
            user_id: User ID
            limit: Maximum number of CVs to return

        Returns:
            JSON string with list of CVs
        """
        try:
            from ...services.cv_service import CVService

            result = CVService.get_user_cvs(
                user_id=user_id,
                include_content=False,
                limit=limit,
            )

            # Simplify the response for chat context
            cvs_summary = []
            for cv in result["cvs"]:
                cvs_summary.append(
                    {
                        "id": cv["id"],
                        "title": cv["title"],
                        "is_ai_generated": cv["is_ai_generated"],
                        "target_position": cv.get("target_position"),
                        "created_at": cv["created_at"],
                        "job_offer": cv.get("job_offer"),
                    }
                )

            return json.dumps(
                {
                    "success": True,
                    "count": len(cvs_summary),
                    "total": result["total"],
                    "cvs": cvs_summary,
                }
            )

        except Exception as e:
            logger.error(f"Error listing CVs: {e}", exc_info=True)
            return json.dumps(
                {
                    "success": False,
                    "error": str(e),
                }
            )

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a tool by name with given arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result as JSON string
        """
        if tool_name == "search_jobs":
            return self.search_jobs(**arguments)
        elif tool_name == "get_job_details":
            return self.get_job_details(**arguments)
        elif tool_name == "get_user_profile":
            return self.get_user_profile(**arguments)
        elif tool_name == "generate_cv":
            return self.generate_cv(**arguments)
        elif tool_name == "list_user_cvs":
            return self.list_user_cvs(**arguments)
        else:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}",
                }
            )

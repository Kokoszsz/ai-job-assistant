"""
Profile Context Builder
=======================
Formats user profile data into context for AI personalization.
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProfileContextBuilder:
    """Builds AI context from user profile data."""

    @staticmethod
    def build_user_context(user_id: int, profile_data: Dict[str, Any]) -> str:
        """
        Build formatted context string from profile.

        Args:
            user_id: User ID
            profile_data: Profile dict with include_details=True

        Returns:
            Formatted context string for system prompt
        """
        if not profile_data:
            logger.warning(f"No profile data for user {user_id}")
            return ""

        try:
            # Extract user info
            from src.models.base import db
            from src.models.user import User

            user = db.session.query(User).filter_by(id=user_id).first()
            name = user.name if user else "User"

            # Build context sections
            location = profile_data.get("location") or "Not specified"

            # Professional background
            work_experiences = profile_data.get("work_experiences", [])
            experience_level = ProfileContextBuilder.calculate_experience_level(work_experiences)
            current_role = ProfileContextBuilder._get_current_role(work_experiences)

            # Skills
            skills = profile_data.get("skills", [])
            skills_text = ProfileContextBuilder.format_skills(skills)

            # Education
            education = profile_data.get("education", [])
            education_text = ProfileContextBuilder.format_education(education)

            # Job preferences
            preferences = profile_data.get("preferences", {})
            preferences_text = ProfileContextBuilder._format_preferences(preferences)

            # Build complete context
            context_parts = [
                "=== USER PROFILE ===",
                f"Name: {name}",
                f"Location: {location}",
                "",
                "Professional Background:",
                f"- Experience Level: {experience_level}",
            ]

            if current_role:
                context_parts.append(f"- Current/Recent Role: {current_role}")

            if work_experiences:
                years = ProfileContextBuilder._calculate_total_years(work_experiences)
                context_parts.append(f"- Years of Experience: {years}")

            context_parts.extend(["", skills_text, "", education_text, ""])

            # Add certifications if available
            certifications = profile_data.get("certifications", [])
            if certifications:
                certs_text = ProfileContextBuilder.format_certifications(certifications)
                context_parts.extend(["", certs_text])

            # Add projects if available
            projects = profile_data.get("projects", [])
            if projects:
                projects_text = ProfileContextBuilder.format_projects(projects)
                context_parts.extend(["", projects_text])

            # Add languages if available
            languages = profile_data.get("languages", [])
            if languages:
                languages_text = ProfileContextBuilder.format_languages(languages)
                context_parts.extend(["", languages_text])

            context_parts.append("")
            context_parts.extend(preferences_text)
            context_parts.append("===================")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error building user context for user {user_id}: {str(e)}")
            return ""

    @staticmethod
    def calculate_experience_level(work_experiences: List[Dict[str, Any]]) -> str:
        """
        Calculate experience level from work history.

        Args:
            work_experiences: List of work experience dictionaries

        Returns:
            Experience level: Entry level, Junior, Mid-level, Senior, or Lead
        """
        if not work_experiences:
            return "Entry level"

        total_years = ProfileContextBuilder._calculate_total_years(work_experiences)

        if total_years < 2:
            return "Entry level"
        elif total_years < 5:
            return "Junior"
        elif total_years < 8:
            return "Mid-level"
        elif total_years < 12:
            return "Senior"
        else:
            return "Lead"

    @staticmethod
    def format_skills(skills: List[Dict[str, Any]], max_skills: int = 8) -> str:
        """
        Format top skills by proficiency.

        Args:
            skills: List of skill dictionaries
            max_skills: Maximum number of skills to include

        Returns:
            Formatted skills string
        """
        if not skills:
            return "Skills: No skills listed"

        # Sort by proficiency level priority
        proficiency_order = {
            "expert": 0,
            "advanced": 1,
            "intermediate": 2,
            "beginner": 3,
        }

        sorted_skills = sorted(
            skills,
            key=lambda s: proficiency_order.get(s.get("proficiency_level", "beginner"), 3),
        )

        # Take top N skills
        top_skills = sorted_skills[:max_skills]

        # Format as "SkillName (Level)"
        skill_strings = [f"{s['name']} ({s.get('proficiency_level', 'intermediate').capitalize()})" for s in top_skills]

        skills_count = len(skills)
        return f"Skills ({skills_count} total):\n- " + "\n- ".join(skill_strings)

    @staticmethod
    def format_education(education_list: List[Dict[str, Any]]) -> str:
        """
        Format education summary.

        Args:
            education_list: List of education dictionaries

        Returns:
            Formatted education string
        """
        if not education_list:
            return "Education: Not specified"

        edu_strings = []
        for edu in education_list:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            field = edu.get("field_of_study", "")
            end_date = edu.get("end_date", "")

            # Extract year from end_date if available
            year = ""
            if end_date:
                try:
                    year = f" ({end_date[:4]})"
                except (IndexError, TypeError):
                    pass

            # Format: "BS Computer Science, Stanford University (2016)"
            parts = []
            if degree:
                if field:
                    parts.append(f"{degree} {field}")
                else:
                    parts.append(degree)

            if institution:
                if parts:
                    edu_string = f"{parts[0]}, {institution}{year}"
                else:
                    edu_string = f"{institution}{year}"
            else:
                edu_string = parts[0] if parts else ""

            if edu_string:
                edu_strings.append(edu_string)

        if not edu_strings:
            return "Education: Not specified"

        return "Education:\n- " + "\n- ".join(edu_strings)

    @staticmethod
    def _get_current_role(work_experiences: List[Dict[str, Any]]) -> Optional[str]:
        """Get current or most recent role."""
        if not work_experiences:
            return None

        # Work experiences are already sorted by start_date desc
        for exp in work_experiences:
            job_title = exp.get("job_title", "")
            company = exp.get("company", "")
            is_current = exp.get("is_current", False)

            if job_title and company:
                if is_current:
                    return f"{job_title} at {company} (Current)"
                else:
                    return f"{job_title} at {company}"

        return None

    @staticmethod
    def _calculate_total_years(work_experiences: List[Dict[str, Any]]) -> int:
        """Calculate total years of experience."""
        if not work_experiences:
            return 0

        total_days = 0
        for exp in work_experiences:
            start_date_str = exp.get("start_date")
            end_date_str = exp.get("end_date")

            if not start_date_str:
                continue

            try:
                # Parse dates
                start_date = date.fromisoformat(start_date_str) if isinstance(start_date_str, str) else start_date_str

                # Use current date if still employed
                if end_date_str:
                    end_date = date.fromisoformat(end_date_str) if isinstance(end_date_str, str) else end_date_str
                else:
                    end_date = date.today()

                # Calculate days
                days = (end_date - start_date).days
                if days > 0:
                    total_days += days

            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing work experience dates: {e}")
                continue

        # Convert to years (rounded)
        total_years = round(total_days / 365)
        return total_years

    @staticmethod
    def format_certifications(certifications: List[Dict[str, Any]], max_certs: int = 5) -> str:
        """
        Format certifications summary.

        Args:
            certifications: List of certification dictionaries
            max_certs: Maximum number of certifications to include

        Returns:
            Formatted certifications string
        """
        if not certifications:
            return "Certifications: None listed"

        cert_strings = []
        for cert in certifications[:max_certs]:
            name = cert.get("name", "")
            issuer = cert.get("issuing_organization", "")
            issue_date = cert.get("issue_date", "")
            is_valid = cert.get("is_valid", True)

            if name and issuer:
                year = ""
                if issue_date:
                    try:
                        year = f" ({issue_date[:4]})"
                    except (IndexError, TypeError):
                        pass

                validity = " [EXPIRED]" if not is_valid else ""
                cert_strings.append(f"{name}, {issuer}{year}{validity}")

        if not cert_strings:
            return "Certifications: None listed"

        certs_count = len(certifications)
        return f"Certifications ({certs_count} total):\n- " + "\n- ".join(cert_strings)

    @staticmethod
    def format_projects(projects: List[Dict[str, Any]], max_projects: int = 4) -> str:
        """
        Format projects summary.

        Args:
            projects: List of project dictionaries
            max_projects: Maximum number of projects to include

        Returns:
            Formatted projects string
        """
        if not projects:
            return "Projects: None listed"

        project_strings = []
        for proj in projects[:max_projects]:
            name = proj.get("name", "")
            description = proj.get("description", "")
            technologies = proj.get("technologies", [])

            if name:
                # Truncate description if too long
                if description and len(description) > 100:
                    description = description[:97] + "..."

                tech_str = ""
                if technologies:
                    if isinstance(technologies, list):
                        tech_str = f" [{', '.join(technologies[:4])}]"
                    else:
                        tech_str = f" [{technologies}]"

                project_str = name
                if description:
                    project_str += f": {description}"
                project_str += tech_str

                project_strings.append(project_str)

        if not project_strings:
            return "Projects: None listed"

        projects_count = len(projects)
        return f"Projects ({projects_count} total):\n- " + "\n- ".join(project_strings)

    @staticmethod
    def format_languages(languages: List[Dict[str, Any]]) -> str:
        """
        Format languages summary.

        Args:
            languages: List of language dictionaries

        Returns:
            Formatted languages string
        """
        if not languages:
            return "Languages: Not specified"

        lang_strings = []
        for lang in languages:
            name = lang.get("name", "")
            proficiency = lang.get("proficiency_label") or lang.get("proficiency_level", "")

            if name:
                if proficiency:
                    lang_strings.append(f"{name} ({proficiency})")
                else:
                    lang_strings.append(name)

        if not lang_strings:
            return "Languages: Not specified"

        return f"Languages:\n- " + "\n- ".join(lang_strings)

    @staticmethod
    def _format_preferences(preferences: Dict[str, Any]) -> List[str]:
        """Format job preferences."""
        lines = ["Job Preferences:"]

        desired_roles = preferences.get("desired_roles", [])
        if desired_roles:
            if isinstance(desired_roles, list):
                lines.append(f"- Desired Roles: {', '.join(desired_roles)}")
            else:
                lines.append(f"- Desired Roles: {desired_roles}")
        else:
            lines.append("- Desired Roles: Not specified")

        locations = preferences.get("locations", [])
        if locations:
            if isinstance(locations, list):
                lines.append(f"- Preferred Locations: {', '.join(locations)}")
            else:
                lines.append(f"- Preferred Locations: {locations}")
        else:
            lines.append("- Preferred Locations: Not specified")

        job_types = preferences.get("job_types", [])
        if job_types:
            if isinstance(job_types, list):
                formatted_types = [jt.capitalize() for jt in job_types]
                lines.append(f"- Job Types: {', '.join(formatted_types)}")
            else:
                lines.append(f"- Job Types: {job_types}")
        else:
            lines.append("- Job Types: Not specified")

        min_salary = preferences.get("min_salary")
        max_salary = preferences.get("max_salary")
        if min_salary or max_salary:
            if min_salary and max_salary:
                lines.append(f"- Salary Range: ${min_salary:,} - ${max_salary:,}")
            elif min_salary:
                lines.append(f"- Minimum Salary: ${min_salary:,}")
            elif max_salary:
                lines.append(f"- Maximum Salary: ${max_salary:,}")
        else:
            lines.append("- Salary Range: Not specified")

        experience_level = preferences.get("experience_level")
        if experience_level:
            lines.append(f"- Experience Level Sought: {experience_level.capitalize()}")

        return lines

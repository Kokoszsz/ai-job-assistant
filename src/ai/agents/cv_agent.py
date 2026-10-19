"""
CV Generation Agent
===================
Specialized AI agent for generating professional CVs from user profiles.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# System prompt for CV generation
CV_GENERATION_SYSTEM_PROMPT = """You are an expert CV/resume writer with 15+ years of experience in career consulting and recruitment. Your role is to create compelling, professional CVs that help candidates stand out.

## Your Expertise:
- Creating ATS (Applicant Tracking System) optimized resumes
- Highlighting achievements with quantifiable metrics
- Using powerful action verbs and impactful language
- Tailoring CVs to specific job requirements
- Following current industry best practices

## CV Writing Guidelines:
1. **Professional Summary**: Write a compelling 2-3 sentence summary that captures the candidate's value proposition
2. **Experience**: Focus on achievements, not just duties. Use the STAR method (Situation, Task, Action, Result)
3. **Skills**: Organize skills by category (technical, soft skills) and prioritize by relevance
4. **Education**: Include relevant details, honors, and relevant coursework if applicable
5. **Formatting**: Use consistent formatting, bullet points, and clear section headers

## Important Rules:
- ALWAYS return valid JSON in the specified format
- DO NOT fabricate or invent information - only use what's provided in the profile
- DO enhance and improve the wording of existing information
- DO reorganize and prioritize information for maximum impact
- Use action verbs: Led, Developed, Implemented, Achieved, Increased, Reduced, etc.
- Quantify achievements whenever possible (percentages, numbers, dollar amounts)
- Keep bullet points concise (1-2 lines each)
- For current positions, use present tense; for past positions, use past tense

Current date: {current_date}
"""

# JSON schema for CV content
CV_JSON_SCHEMA = """
{
  "personal": {
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "+1234567890 (or null if not provided)",
    "location": "City, State/Country (or null if not provided)",
    "linkedin": "linkedin.com/in/username (or null if not provided)",
    "website": "personal-website.com (or null if not provided)"
  },
  "summary": "A compelling 2-3 sentence professional summary highlighting key strengths and career objectives",
  "experience": [
    {
      "title": "Job Title",
      "company": "Company Name",
      "location": "City, State (optional)",
      "start_date": "YYYY-MM",
      "end_date": "YYYY-MM or null if current",
      "current": true/false,
      "highlights": [
        "Achievement-focused bullet point with metrics where possible",
        "Another impactful accomplishment"
      ]
    }
  ],
  "education": [
    {
      "degree": "Degree Type (e.g., Bachelor of Science)",
      "field": "Field of Study",
      "institution": "University/College Name",
      "start_date": "YYYY-MM",
      "end_date": "YYYY-MM or null if ongoing",
      "gpa": "GPA if notable (optional)",
      "honors": "Honors/Awards (optional)"
    }
  ],
  "skills": {
    "technical": ["Skill 1", "Skill 2", "..."],
    "soft": ["Leadership", "Communication", "..."],
    "tools": ["Tool 1", "Tool 2", "..."]
  },
  "sections": {
    "certifications": [
      {
        "name": "Certification Name",
        "issuer": "Issuing Organization",
        "date": "YYYY-MM",
        "expires": "YYYY-MM or null"
      }
    ],
    "projects": [
      {
        "name": "Project Name",
        "description": "Brief description",
        "technologies": ["Tech 1", "Tech 2"],
        "url": "project-url.com (optional)"
      }
    ],
    "languages": [
      {
        "name": "Language",
        "proficiency": "Native/Fluent/Professional/Basic"
      }
    ]
  }
}
"""


class CVGenerationAgent:
    """
    Specialized agent for generating professional CVs.

    This agent uses OpenAI to transform user profile data into
    well-formatted, professional CV content.
    """

    def __init__(self, ai_service):
        """
        Initialize CV generation agent.

        Args:
            ai_service: AIService instance for OpenAI access
        """
        self.ai_service = ai_service
        self._agent = None

    def _get_agent(self):
        """Get or create the base agent."""
        if self._agent is None:
            self._agent = self.ai_service.create_agent(
                temperature=0.7,  # Some creativity for writing
                max_tokens=4000,  # CVs can be lengthy
            )

            # Set system prompt
            current_date = datetime.utcnow().strftime("%Y-%m-%d")
            system_prompt = CV_GENERATION_SYSTEM_PROMPT.format(current_date=current_date)
            self._agent.initialize_conversation(system_prompt=system_prompt)

        return self._agent

    def generate_generic_cv(self, profile_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a generic professional CV from user profile.

        Args:
            profile_context: Dictionary containing user profile data
                - personal: {name, email, phone, location}
                - summary: Professional summary text
                - work_experiences: List of work experience dicts
                - education: List of education dicts
                - skills: List of skill dicts
                - certifications: List of certification dicts (optional)
                - projects: List of project dicts (optional)
                - languages: List of language dicts (optional)

        Returns:
            CV content dictionary in the standard format

        Raises:
            ValueError: If generation fails
        """
        try:
            agent = self._get_agent()

            # Build the prompt
            prompt = self._build_generic_prompt(profile_context)

            # Get AI response
            response = agent.send_message(prompt)

            # Parse JSON from response
            cv_content = self._parse_cv_response(response)

            logger.info("Successfully generated generic CV")
            return cv_content

        except Exception as e:
            logger.error(f"Error generating generic CV: {str(e)}")
            raise ValueError(f"Failed to generate CV: {str(e)}")

    def generate_tailored_cv(self, profile_context: Dict[str, Any], job_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a CV tailored to a specific job offer.

        Args:
            profile_context: Dictionary containing user profile data
            job_context: Dictionary containing job offer details
                - title: Job title
                - company: Company name
                - location: Job location
                - description: Job description
                - requirements: Job requirements
                - job_type: Type of employment

        Returns:
            Tailored CV content dictionary

        Raises:
            ValueError: If generation fails
        """
        try:
            agent = self._get_agent()

            # Build the prompt
            prompt = self._build_tailored_prompt(profile_context, job_context)

            # Get AI response
            response = agent.send_message(prompt)

            # Parse JSON from response
            cv_content = self._parse_cv_response(response)

            logger.info(f"Successfully generated tailored CV for: {job_context.get('title')}")
            return cv_content

        except Exception as e:
            logger.error(f"Error generating tailored CV: {str(e)}")
            raise ValueError(f"Failed to generate tailored CV: {str(e)}")

    def refine_section(self, cv_content: Dict[str, Any], section_name: str, instruction: str) -> Dict[str, Any]:
        """
        Refine a specific section of the CV based on user feedback.

        Args:
            cv_content: Current CV content
            section_name: Name of section to refine (e.g., 'summary', 'experience')
            instruction: User's instruction for refinement

        Returns:
            Updated CV content with refined section

        Raises:
            ValueError: If refinement fails
        """
        try:
            agent = self._get_agent()

            prompt = f"""Please refine the '{section_name}' section of this CV based on the following instruction:

Instruction: {instruction}

Current CV content:
```json
{json.dumps(cv_content, indent=2)}
```

Return the COMPLETE updated CV in JSON format with the refined section. Keep all other sections unchanged.

Return ONLY valid JSON, no additional text."""

            response = agent.send_message(prompt)
            cv_content = self._parse_cv_response(response)

            logger.info(f"Successfully refined CV section: {section_name}")
            return cv_content

        except Exception as e:
            logger.error(f"Error refining CV section {section_name}: {str(e)}")
            raise ValueError(f"Failed to refine CV section: {str(e)}")

    def _build_generic_prompt(self, profile_context: Dict[str, Any]) -> str:
        """Build prompt for generic CV generation."""
        prompt = f"""Generate a professional CV from the following profile data. Create a compelling, ATS-friendly resume that highlights the candidate's strengths and achievements.

## Profile Data:
```json
{json.dumps(profile_context, indent=2, default=str)}
```

## Requirements:
1. Write a compelling professional summary (2-3 sentences)
2. Transform work experience into achievement-focused bullet points
3. Organize skills by category
4. Include all relevant certifications, projects, and languages
5. Use action verbs and quantify achievements where possible

## Output Format:
Return ONLY valid JSON matching this schema (no additional text, no markdown code blocks around the JSON):

{CV_JSON_SCHEMA}

Important: 
- Only use information provided in the profile data
- Enhance wording but don't fabricate new facts
- If a field is not available in the profile, use null or omit it
- Format dates as YYYY-MM
- Return the JSON directly, not wrapped in code blocks"""

        return prompt

    def _build_tailored_prompt(self, profile_context: Dict[str, Any], job_context: Dict[str, Any]) -> str:
        """Build prompt for tailored CV generation."""
        prompt = f"""Generate a CV tailored specifically for this job opportunity. Emphasize experiences and skills most relevant to the role.

## Target Job:
- **Position**: {job_context.get("title", "N/A")}
- **Company**: {job_context.get("company", "N/A")}
- **Location**: {job_context.get("location", "N/A")}
- **Job Type**: {job_context.get("job_type", "N/A")}

**Job Description**:
{job_context.get("description", "No description provided")}

**Requirements**:
{job_context.get("requirements", "No specific requirements listed")}

## Candidate Profile:
```json
{json.dumps(profile_context, indent=2, default=str)}
```

## Tailoring Instructions:
1. **Summary**: Write a summary that directly addresses what this employer is looking for
2. **Experience**: 
   - Reorder experiences to put most relevant first
   - Emphasize achievements that match job requirements
   - Use keywords from the job description naturally
3. **Skills**: 
   - Prioritize skills mentioned in the job posting
   - Group technical skills relevant to this role first
4. **Projects/Certifications**: Highlight those most relevant to this position

## Output Format:
Return ONLY valid JSON matching this schema (no additional text, no markdown code blocks):

{CV_JSON_SCHEMA}

Important:
- Only use information from the candidate's profile - don't invent new experiences
- Enhance and reorganize existing information for maximum relevance
- Include keywords from the job description where they naturally fit
- Format dates as YYYY-MM
- Return the JSON directly, not wrapped in code blocks"""

        return prompt

    def _parse_cv_response(self, response: str) -> Dict[str, Any]:
        """
        Parse CV JSON from AI response.

        Args:
            response: Raw AI response text

        Returns:
            Parsed CV content dictionary

        Raises:
            ValueError: If parsing fails
        """
        try:
            # Clean up response - remove markdown code blocks if present
            cleaned = response.strip()

            # Remove ```json and ``` markers
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]

            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            cleaned = cleaned.strip()

            # Try to find JSON object in response
            # Sometimes AI adds text before/after JSON
            json_match = re.search(r"\{[\s\S]*\}", cleaned)
            if json_match:
                cleaned = json_match.group(0)

            # Parse JSON
            cv_content = json.loads(cleaned)

            # Validate basic structure
            if not isinstance(cv_content, dict):
                raise ValueError("CV content must be a dictionary")

            if "personal" not in cv_content:
                raise ValueError("CV content missing 'personal' section")

            if "summary" not in cv_content:
                raise ValueError("CV content missing 'summary' section")

            return cv_content

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CV JSON: {str(e)}")
            logger.debug(f"Raw response: {response[:500]}...")
            raise ValueError(f"AI response was not valid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing CV response: {str(e)}")
            raise ValueError(f"Failed to parse CV response: {str(e)}")

"""
Remotive API Client
===================
Client for fetching IT/tech job listings from the Remotive API.

Remotive is a free job board API focused on remote tech jobs.
No API key required.

API Documentation: https://remotive.com/api/remote-jobs
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
import html2text

logger = logging.getLogger(__name__)

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"

# Remotive job categories (IT-focused)
REMOTIVE_CATEGORIES = [
    "software-dev",
    "devops",
    "data",
    "product",
    "design",
    "qa",
    "customer-support",
    "marketing",
    "sales",
    "hr",
    "finance",
    "writing",
    "all-others",
]


class RemotiveAPIError(Exception):
    """Exception raised when Remotive API request fails."""

    pass


class RemotiveClient:
    """
    Client for the Remotive API.

    Example usage:
        client = RemotiveClient()
        jobs = client.fetch_jobs(category="software-dev")
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize the Remotive client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.base_url = REMOTIVE_API_URL

    def fetch_jobs(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch jobs from Remotive API.

        Args:
            category: Job category filter (e.g., "software-dev", "devops")
            search: Search keyword
            limit: Maximum number of jobs to return

        Returns:
            List of job dictionaries from the API

        Raises:
            RemotiveAPIError: If the API request fails
        """
        params = {}
        if category and category in REMOTIVE_CATEGORIES:
            params["category"] = category
        if search:
            params["search"] = search
        if limit:
            params["limit"] = limit

        try:
            logger.info(f"Fetching jobs from Remotive API with params: {params}")

            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "JobSearchAssistant/1.0"},
            )
            response.raise_for_status()

            data = response.json()
            jobs = data.get("jobs", [])

            logger.info(f"Fetched {len(jobs)} jobs from Remotive API")
            return jobs

        except requests.exceptions.Timeout:
            logger.error("Remotive API request timed out")
            raise RemotiveAPIError("Request to Remotive API timed out")
        except requests.exceptions.RequestException as e:
            logger.error(f"Remotive API request failed: {e}")
            raise RemotiveAPIError(f"Failed to fetch jobs from Remotive: {e}")
        except ValueError as e:
            logger.error(f"Failed to parse Remotive API response: {e}")
            raise RemotiveAPIError(f"Invalid response from Remotive API: {e}")

    @staticmethod
    def html_to_text(html_content: Optional[str]) -> Optional[str]:
        """
        Convert HTML content to plain text.

        Args:
            html_content: HTML string

        Returns:
            Plain text string with HTML tags removed
        """
        if not html_content:
            return None

        try:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.ignore_emphasis = False
            h.body_width = 0  # Don't wrap lines
            h.single_line_break = True

            text = h.handle(html_content)
            # Clean up excessive newlines
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text.strip()
        except Exception as e:
            logger.warning(f"Failed to convert HTML to text: {e}")
            # Fallback: simple tag stripping
            return re.sub(r'<[^>]+>', '', html_content).strip()

    @staticmethod
    def parse_salary(salary_text: Optional[str]) -> tuple[Optional[int], Optional[int]]:
        """
        Parse salary text into min/max integers.

        Handles various formats:
        - "50000 - 80000"
        - "$50,000 - $80,000"
        - "50k - 80k"
        - "50K-80K USD"
        - "$120,000"

        Args:
            salary_text: Raw salary string from API

        Returns:
            Tuple of (salary_min, salary_max), either or both can be None
        """
        if not salary_text:
            return None, None

        salary_text = salary_text.strip().upper()

        # Remove common currency symbols and words
        salary_text = re.sub(r"[£€$]", "", salary_text)
        salary_text = re.sub(
            r"\b(USD|EUR|GBP|PER YEAR|YEARLY|ANNUAL|PA|P\.A\.)\b",
            "",
            salary_text,
            flags=re.IGNORECASE,
        )
        salary_text = salary_text.strip()

        # Convert "K" notation to thousands
        salary_text = re.sub(
            r"(\d+)K", lambda m: str(int(m.group(1)) * 1000), salary_text
        )

        # Remove commas from numbers
        salary_text = salary_text.replace(",", "")

        # Try to find number range (e.g., "50000 - 80000" or "50000-80000")
        range_match = re.search(r"(\d+)\s*[-–—to]+\s*(\d+)", salary_text)
        if range_match:
            try:
                min_val = int(range_match.group(1))
                max_val = int(range_match.group(2))
                return min_val, max_val
            except ValueError:
                pass

        # Try to find single number
        single_match = re.search(r"(\d+)", salary_text)
        if single_match:
            try:
                val = int(single_match.group(1))
                # If it's a reasonable salary (at least 10k), use it
                if val >= 10000:
                    return val, val
            except ValueError:
                pass

        return None, None

    @staticmethod
    def normalize_job_type(job_type: Optional[str]) -> str:
        """
        Normalize Remotive job type to our standard job types.

        Args:
            job_type: Job type from Remotive API

        Returns:
            Normalized job type string
        """
        if not job_type:
            return "remote"

        job_type = job_type.lower().strip()

        type_mapping = {
            "full_time": "full-time",
            "full-time": "full-time",
            "fulltime": "full-time",
            "part_time": "part-time",
            "part-time": "part-time",
            "parttime": "part-time",
            "contract": "contract",
            "contractor": "contract",
            "freelance": "contract",
            "internship": "internship",
            "intern": "internship",
        }

        return type_mapping.get(job_type, "remote")

    @staticmethod
    def map_job_to_model(job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map a Remotive API job to our JobOffer model fields.

        Args:
            job: Raw job dictionary from Remotive API

        Returns:
            Dictionary with fields matching JobOffer model
        """
        # Parse salary
        salary_min, salary_max = RemotiveClient.parse_salary(job.get("salary"))

        # Parse publication date
        pub_date_str = job.get("publication_date")
        posted_date = None
        if pub_date_str:
            try:
                # Remotive uses ISO format: "2026-01-15T12:00:00"
                posted_date = datetime.fromisoformat(
                    pub_date_str.replace("Z", "+00:00")
                ).date()
            except (ValueError, AttributeError):
                posted_date = datetime.utcnow().date()
        else:
            posted_date = datetime.utcnow().date()

        # Get tags as list
        tags = job.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        # Convert HTML description to plain text
        description_html = job.get("description", "")
        description_text = RemotiveClient.html_to_text(description_html) or ""

        return {
            "external_id": str(job.get("id")),
            "external_source": "remotive",
            "title": job.get("title", "Unknown Title"),
            "company": job.get("company_name", "Unknown Company"),
            "location": job.get("candidate_required_location", "Remote"),
            "description": description_text,
            "requirements": None,  # Remotive doesn't separate requirements
            "salary_min": salary_min,
            "salary_max": salary_max,
            "job_type": RemotiveClient.normalize_job_type(job.get("job_type")),
            "posted_date": posted_date,
            "external_url": job.get("url"),
            "is_active": True,
            "tags": tags if tags else None,
            "category": job.get("category"),
            "company_logo_url": job.get("company_logo"),
            "last_seen_at": datetime.utcnow(),
        }

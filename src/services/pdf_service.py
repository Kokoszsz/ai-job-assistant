"""
PDF Export Service
==================
Generate professional PDF documents from CV content using ReportLab.
"""

import io
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


class PDFService:
    """Service for generating PDF documents from CV content."""

    # Page configuration
    PAGE_SIZE = A4
    MARGIN_LEFT = 0.75 * inch
    MARGIN_RIGHT = 0.75 * inch
    MARGIN_TOP = 0.5 * inch
    MARGIN_BOTTOM = 0.5 * inch

    # Colors
    PRIMARY_COLOR = colors.HexColor("#2563eb")  # Blue
    TEXT_COLOR = colors.HexColor("#1f2937")  # Dark gray
    SECONDARY_TEXT = colors.HexColor("#6b7280")  # Medium gray
    BORDER_COLOR = colors.HexColor("#e5e7eb")  # Light gray

    @classmethod
    def generate_cv_pdf(cls, cv_content: Dict[str, Any], title: str = "CV") -> bytes:
        """
        Generate a PDF from CV content.

        Args:
            cv_content: CV content dictionary (matches CV JSON schema)
            title: Document title

        Returns:
            PDF file as bytes
        """
        buffer = io.BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=cls.PAGE_SIZE,
            leftMargin=cls.MARGIN_LEFT,
            rightMargin=cls.MARGIN_RIGHT,
            topMargin=cls.MARGIN_TOP,
            bottomMargin=cls.MARGIN_BOTTOM,
            title=title,
        )

        # Build content
        styles = cls._get_styles()
        story = []

        # Personal info / Header
        personal = cv_content.get("personal", {})
        story.extend(cls._build_header(personal, styles))

        # Professional Summary
        summary = cv_content.get("summary", "")
        if summary:
            story.extend(cls._build_summary(summary, styles))

        # Work Experience
        experience = cv_content.get("experience", [])
        if experience:
            story.extend(cls._build_experience(experience, styles))

        # Education
        education = cv_content.get("education", [])
        if education:
            story.extend(cls._build_education(education, styles))

        # Skills
        skills = cv_content.get("skills", {})
        if skills:
            story.extend(cls._build_skills(skills, styles))

        # Additional Sections (certifications, projects, languages)
        sections = cv_content.get("sections", {})
        if sections:
            story.extend(cls._build_additional_sections(sections, styles))

        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        logger.info(f"Generated PDF for CV: {title} ({len(pdf_bytes)} bytes)")
        return pdf_bytes

    @classmethod
    def _get_styles(cls) -> Dict[str, ParagraphStyle]:
        """Create custom styles for the CV PDF."""
        base_styles = getSampleStyleSheet()

        styles = {
            "name": ParagraphStyle(
                "CVName",
                parent=base_styles["Heading1"],
                fontSize=24,
                textColor=cls.TEXT_COLOR,
                spaceAfter=2,
                alignment=TA_CENTER,
            ),
            "contact": ParagraphStyle(
                "CVContact",
                parent=base_styles["Normal"],
                fontSize=10,
                textColor=cls.SECONDARY_TEXT,
                alignment=TA_CENTER,
                spaceAfter=12,
            ),
            "section_header": ParagraphStyle(
                "CVSectionHeader",
                parent=base_styles["Heading2"],
                fontSize=13,
                textColor=cls.PRIMARY_COLOR,
                spaceBefore=14,
                spaceAfter=6,
                borderPadding=0,
            ),
            "subsection_header": ParagraphStyle(
                "CVSubsectionHeader",
                parent=base_styles["Heading3"],
                fontSize=11,
                textColor=cls.TEXT_COLOR,
                spaceBefore=8,
                spaceAfter=2,
                fontName="Helvetica-Bold",
            ),
            "normal": ParagraphStyle(
                "CVNormal",
                parent=base_styles["Normal"],
                fontSize=10,
                textColor=cls.TEXT_COLOR,
                alignment=TA_JUSTIFY,
                leading=14,
            ),
            "summary": ParagraphStyle(
                "CVSummary",
                parent=base_styles["Normal"],
                fontSize=10,
                textColor=cls.TEXT_COLOR,
                alignment=TA_JUSTIFY,
                leading=14,
                spaceAfter=6,
            ),
            "company": ParagraphStyle(
                "CVCompany",
                parent=base_styles["Normal"],
                fontSize=10,
                textColor=cls.SECONDARY_TEXT,
                spaceAfter=4,
            ),
            "date_range": ParagraphStyle(
                "CVDateRange",
                parent=base_styles["Normal"],
                fontSize=9,
                textColor=cls.SECONDARY_TEXT,
                alignment=TA_LEFT,
            ),
            "bullet": ParagraphStyle(
                "CVBullet",
                parent=base_styles["Normal"],
                fontSize=10,
                textColor=cls.TEXT_COLOR,
                leftIndent=12,
                spaceBefore=2,
                spaceAfter=2,
                leading=13,
            ),
            "skill_category": ParagraphStyle(
                "CVSkillCategory",
                parent=base_styles["Normal"],
                fontSize=10,
                textColor=cls.TEXT_COLOR,
                fontName="Helvetica-Bold",
                spaceBefore=4,
                spaceAfter=2,
            ),
            "skills_text": ParagraphStyle(
                "CVSkillsText",
                parent=base_styles["Normal"],
                fontSize=10,
                textColor=cls.TEXT_COLOR,
                spaceAfter=4,
            ),
        }

        return styles

    @classmethod
    def _build_header(cls, personal: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> list:
        """Build the header section with name and contact info."""
        story = []

        # Name
        name = personal.get("name", "")
        if name:
            story.append(Paragraph(name, styles["name"]))

        # Contact info line
        contact_parts = []

        email = personal.get("email", "")
        if email:
            contact_parts.append(email)

        phone = personal.get("phone", "")
        if phone:
            contact_parts.append(phone)

        location = personal.get("location", "")
        if location:
            contact_parts.append(location)

        if contact_parts:
            contact_line = " | ".join(contact_parts)
            story.append(Paragraph(contact_line, styles["contact"]))

        # Links line (LinkedIn, Website)
        link_parts = []

        linkedin = personal.get("linkedin", "")
        if linkedin:
            # Extract username or show URL
            if "linkedin.com/in/" in linkedin:
                link_parts.append(f"LinkedIn: {linkedin}")
            else:
                link_parts.append(f"LinkedIn: {linkedin}")

        website = personal.get("website", "")
        if website:
            link_parts.append(f"Portfolio: {website}")

        if link_parts:
            links_line = " | ".join(link_parts)
            story.append(Paragraph(links_line, styles["contact"]))

        # Separator line
        story.append(
            HRFlowable(
                width="100%",
                thickness=1,
                color=cls.BORDER_COLOR,
                spaceBefore=6,
                spaceAfter=6,
            )
        )

        return story

    @classmethod
    def _build_summary(cls, summary: str, styles: Dict[str, ParagraphStyle]) -> list:
        """Build the professional summary section."""
        story = []

        story.append(Paragraph("PROFESSIONAL SUMMARY", styles["section_header"]))
        story.append(Paragraph(summary, styles["summary"]))

        return story

    @classmethod
    def _build_experience(cls, experience: list, styles: Dict[str, ParagraphStyle]) -> list:
        """Build the work experience section."""
        story = []

        story.append(Paragraph("WORK EXPERIENCE", styles["section_header"]))

        for job in experience:
            title = job.get("title", "")
            company = job.get("company", "")
            location = job.get("location", "")

            # Job title
            story.append(Paragraph(title, styles["subsection_header"]))

            # Company and dates
            company_line = company
            if location:
                company_line = f"{company} - {location}"

            start_date = job.get("start_date", "")
            end_date = job.get("end_date", "")
            current = job.get("current", False)

            date_str = cls._format_date_range(start_date, end_date, current)
            if date_str:
                company_line = f"{company_line} | {date_str}"

            story.append(Paragraph(company_line, styles["company"]))

            # Highlights/bullets
            highlights = job.get("highlights", [])
            if highlights:
                for highlight in highlights:
                    bullet_text = f"\u2022 {highlight}"
                    story.append(Paragraph(bullet_text, styles["bullet"]))

            story.append(Spacer(1, 6))

        return story

    @classmethod
    def _build_education(cls, education: list, styles: Dict[str, ParagraphStyle]) -> list:
        """Build the education section."""
        story = []

        story.append(Paragraph("EDUCATION", styles["section_header"]))

        for edu in education:
            degree = edu.get("degree", "")
            field = edu.get("field", "")
            institution = edu.get("institution", "")

            # Degree and field
            degree_line = degree
            if field:
                degree_line = f"{degree} in {field}"
            story.append(Paragraph(degree_line, styles["subsection_header"]))

            # Institution and dates
            inst_line = institution

            start_date = edu.get("start_date", "")
            end_date = edu.get("end_date", "")

            date_str = cls._format_date_range(start_date, end_date, False)
            if date_str:
                inst_line = f"{inst_line} | {date_str}"

            gpa = edu.get("gpa", "")
            if gpa:
                inst_line = f"{inst_line} | GPA: {gpa}"

            story.append(Paragraph(inst_line, styles["company"]))
            story.append(Spacer(1, 4))

        return story

    @classmethod
    def _build_skills(cls, skills: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> list:
        """Build the skills section."""
        story = []

        story.append(Paragraph("SKILLS", styles["section_header"]))

        # Technical skills
        technical = skills.get("technical", [])
        if technical:
            skills_text = ", ".join(technical)
            story.append(Paragraph("Technical:", styles["skill_category"]))
            story.append(Paragraph(skills_text, styles["skills_text"]))

        # Soft skills
        soft = skills.get("soft", [])
        if soft:
            skills_text = ", ".join(soft)
            story.append(Paragraph("Soft Skills:", styles["skill_category"]))
            story.append(Paragraph(skills_text, styles["skills_text"]))

        # Tools
        tools = skills.get("tools", [])
        if tools:
            skills_text = ", ".join(tools)
            story.append(Paragraph("Tools:", styles["skill_category"]))
            story.append(Paragraph(skills_text, styles["skills_text"]))

        return story

    @classmethod
    def _build_additional_sections(cls, sections: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> list:
        """Build additional sections (certifications, projects, languages)."""
        story = []

        # Certifications
        certifications = sections.get("certifications", [])
        if certifications:
            story.append(Paragraph("CERTIFICATIONS", styles["section_header"]))
            for cert in certifications:
                name = cert.get("name", "")
                issuer = cert.get("issuer", "")
                date = cert.get("date", cert.get("issue_date", ""))

                cert_line = name
                if issuer:
                    cert_line = f"{name} - {issuer}"
                if date:
                    cert_line = f"{cert_line} ({date})"

                story.append(Paragraph(f"\u2022 {cert_line}", styles["bullet"]))
            story.append(Spacer(1, 4))

        # Projects
        projects = sections.get("projects", [])
        if projects:
            story.append(Paragraph("PROJECTS", styles["section_header"]))
            for project in projects:
                name = project.get("name", "")
                description = project.get("description", "")

                story.append(Paragraph(name, styles["subsection_header"]))
                if description:
                    story.append(Paragraph(description, styles["normal"]))

                # Technologies used
                technologies = project.get("technologies", [])
                if technologies:
                    tech_text = f"Technologies: {', '.join(technologies)}"
                    story.append(Paragraph(tech_text, styles["company"]))

                story.append(Spacer(1, 4))

        # Languages
        languages = sections.get("languages", [])
        if languages:
            story.append(Paragraph("LANGUAGES", styles["section_header"]))
            lang_items = []
            for lang in languages:
                name = lang.get("name", lang.get("language", ""))
                level = lang.get("level", lang.get("proficiency", ""))
                if name and level:
                    lang_items.append(f"{name}: {level}")
                elif name:
                    lang_items.append(name)

            if lang_items:
                lang_text = " | ".join(lang_items)
                story.append(Paragraph(lang_text, styles["normal"]))

        return story

    @staticmethod
    def _format_date_range(start_date: str, end_date: Optional[str], current: bool) -> str:
        """
        Format a date range for display.

        Args:
            start_date: Start date (YYYY-MM format)
            end_date: End date (YYYY-MM format) or None
            current: Whether this is a current position

        Returns:
            Formatted date string (e.g., "Jan 2020 - Present")
        """
        if not start_date:
            return ""

        def format_month_year(date_str: str) -> str:
            """Convert YYYY-MM to 'Mon YYYY' format."""
            try:
                if not date_str:
                    return ""
                parts = date_str.split("-")
                if len(parts) >= 2:
                    year = parts[0]
                    month = int(parts[1])
                    months = [
                        "Jan",
                        "Feb",
                        "Mar",
                        "Apr",
                        "May",
                        "Jun",
                        "Jul",
                        "Aug",
                        "Sep",
                        "Oct",
                        "Nov",
                        "Dec",
                    ]
                    return f"{months[month - 1]} {year}"
                return date_str
            except (ValueError, IndexError):
                return date_str

        start = format_month_year(start_date)

        if current:
            return f"{start} - Present"
        elif end_date:
            end = format_month_year(end_date)
            return f"{start} - {end}"
        else:
            return start

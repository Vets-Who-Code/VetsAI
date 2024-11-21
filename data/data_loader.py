import os
from typing import List
import logging
from pathlib import Path

# Configure logging
ROOT_DIR = Path(__file__).parent.parent
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(ROOT_DIR / 'vetsai.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def parse_mos_file(file_content: str) -> dict:
    """Parse military job code text file content into a structured dictionary."""
    lines = file_content.strip().split('\n')
    job_code, title, description = "", "", []
    parsing_description = False

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("Job Code:"):
            job_code = line.replace("Job Code:", "").strip()
        elif line.startswith("Description:"):
            parsing_description = True
        elif parsing_description:
            description.append(line)

    for line in description:
        if line:
            title = line
            break

    full_text = ' '.join(description).lower()
    category = "general"
    category_keywords = {
        "information_technology": ["technology", "computer", "network", "data", "software", "hardware", "system",
                                   "database"],
        "communications": ["communications", "signal", "radio", "transmission", "telecom"],
        "intelligence": ["intelligence", "analysis", "surveillance", "reconnaissance"],
        "maintenance": ["maintenance", "repair", "technical", "equipment"],
        "cyber": ["cyber", "security", "information assurance", "cryptographic"]
    }

    for cat, keywords in category_keywords.items():
        if any(keyword in full_text for keyword in keywords):
            category = cat
            break

    return {
        "title": title or "Military Professional",
        "category": category,
        "skills": [line for line in description if line and len(line) > 10]
    }


def load_military_job_codes() -> dict:
    base_path = "data/employment_transitions/job_codes"
    job_codes = {}
    branches = {
        "army": {"path": "army", "prefix": "MOS"},
        "air_force": {"path": "air_force", "prefix": "AFSC"},
        "coast_guard": {"path": "coast_guard", "prefix": "RATE"},
        "navy": {"path": "navy", "prefix": "RATE"},
        "marine_corps": {"path": "marine_corps", "prefix": "MOS"}
    }

    for branch, info in branches.items():
        branch_path = os.path.join(base_path, info["path"])
        if os.path.exists(branch_path):
            for file in os.listdir(branch_path):
                if file.endswith('.txt'):
                    try:
                        with open(os.path.join(branch_path, file), 'r') as f:
                            content = f.read()
                            code = file.replace('.txt', '')
                            details = parse_mos_file(content)
                            vwc_mapping = map_to_vwc_path(details.get('category', ''), details.get('skills', []))
                            details.update({
                                'vwc_path': vwc_mapping['path'],
                                'tech_focus': vwc_mapping['tech_focus'],
                                'branch': branch,
                                'code_type': info['prefix']
                            })
                            job_codes[f"{info['prefix']}_{code}"] = details
                    except Exception as e:
                        logger.error(f"Error loading {file}: {e}")
                        continue
    return job_codes


def map_to_vwc_path(category: str, skills: List[str]) -> dict:
    """Map military job categories and skills to VWC tech stack paths."""
    default_path = {
        "path": "Full Stack Development",
        "tech_focus": [
            "JavaScript/TypeScript fundamentals",
            "Next.js and Tailwind for frontend",
            "Python with FastAPI/Django for backend"
        ]
    }

    tech_paths = {
        "information_technology": {
            "path": "Full Stack Development",
            "tech_focus": [
                "JavaScript/TypeScript with focus on system architecture",
                "Next.js for complex web applications",
                "Python backend services with FastAPI"
            ]
        },
        "cyber": {
            "path": "Security-Focused Development",
            "tech_focus": [
                "TypeScript for type-safe applications",
                "Secure API development with FastAPI/Django",
                "AI/ML for security applications"
            ]
        },
        "communications": {
            "path": "Frontend Development",
            "tech_focus": [
                "JavaScript/TypeScript specialization",
                "Advanced Next.js and Tailwind",
                "API integration with Python backends"
            ]
        },
        "intelligence": {
            "path": "AI/ML Development",
            "tech_focus": [
                "Python for data processing",
                "ML model deployment with FastAPI",
                "Next.js for ML application frontends"
            ]
        },
        "maintenance": {
            "path": "Backend Development",
            "tech_focus": [
                "Python backend development",
                "API design with FastAPI/Django",
                "Basic frontend with Next.js"
            ]
        }
    }

    skill_keywords = {
        "programming": "software",
        "database": "data",
        "network": "communications",
        "security": "cyber",
        "analysis": "intelligence"
    }

    if category.lower() in tech_paths:
        return tech_paths[category.lower()]

    for skill in skills:
        skill_lower = skill.lower()
        for keyword, category in skill_keywords.items():
            if keyword in skill_lower and category in tech_paths:
                return tech_paths[category]

    return default_path


def translate_military_code(code: str, job_codes: dict) -> dict:
    """Translate military code to VWC development path."""
    code = code.upper().strip()
    prefixes = ["MOS", "AFSC", "RATE"]
    for prefix in prefixes:
        if code.startswith(prefix):
            code = code.replace(prefix, "").strip()

    possible_codes = [f"MOS_{code}", f"AFSC_{code}", f"RATE_{code}"]

    for possible_code in possible_codes:
        if possible_code in job_codes:
            job_data = job_codes[possible_code]
            return {
                "found": True,
                "data": {
                    "title": job_data.get('title', 'Military Professional'),
                    "branch": job_data.get('branch', 'Military'),
                    "dev_path": job_data.get('vwc_path', 'Full Stack Development'),
                    "tech_focus": job_data.get('tech_focus', []),
                    "skills": job_data.get('skills', [])
                }
            }

    return {
        "found": False,
        "data": {
            "title": "Military Professional",
            "branch": "Military",
            "dev_path": "Full Stack Development",
            "tech_focus": [
                "Start with JavaScript/TypeScript fundamentals",
                "Build projects with Next.js and Tailwind",
                "Learn Python backend development with FastAPI"
            ],
            "skills": [
                "Leadership and team coordination",
                "Problem-solving and adaptation",
                "Project planning and execution"
            ]
        }
    }

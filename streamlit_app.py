import streamlit as st
import os
import logging
from typing import Dict, List
from datetime import datetime
from dotenv import load_dotenv
import openai
import json
import time
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vetsai.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OpenAI API key not found in .env file")

def load_military_job_codes() -> dict:
    """
    Load military job codes from data directories and map them to software development paths.
    Directory structure:
    data/
        employment_transitions/
            job_codes/
                army/
                air_force/
                coast_guard/
                navy/
                marine_corps/
    """
    base_path = "data/employment_transitions/job_codes"
    job_codes = {}
    
    # Map of service branches to their file paths and code prefixes
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
                if file.endswith('.json'):
                    with open(os.path.join(branch_path, file), 'r') as f:
                        try:
                            branch_codes = json.load(f)
                            # Add VWC specific development paths to each job code
                            for code, details in branch_codes.items():
                                vwc_mapping = map_to_vwc_path(details.get('category', ''), 
                                                            details.get('skills', []))
                                details.update({
                                    'vwc_path': vwc_mapping['path'],
                                    'tech_focus': vwc_mapping['tech_focus'],
                                    'branch': branch,
                                    'code_type': info['prefix']
                                })
                                job_codes[f"{info['prefix']}_{code}"] = details
                        except json.JSONDecodeError as e:
                            logger.error(f"Error loading {file}: {e}")
                            continue
    
    return job_codes

def map_to_vwc_path(category: str, skills: List[str]) -> dict:
    """Map military job categories and skills to VWC tech stack paths."""
    
    # Default full stack path
    default_path = {
        "path": "Full Stack Development",
        "tech_focus": [
            "JavaScript/TypeScript fundamentals",
            "Next.js and Tailwind for frontend",
            "Python with FastAPI/Django for backend"
        ]
    }
    
    # Category-based mappings
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
    
    # Skill-based adjustments
    skill_keywords = {
        "programming": "software",
        "database": "data",
        "network": "communications",
        "security": "cyber",
        "analysis": "intelligence"
    }
    
    # Determine best path based on category and skills
    if category.lower() in tech_paths:
        return tech_paths[category.lower()]
    
    # Check skills for keywords
    for skill in skills:
        skill_lower = skill.lower()
        for keyword, category in skill_keywords.items():
            if keyword in skill_lower and category in tech_paths:
                return tech_paths[category]
    
    return default_path

def translate_military_code(code: str, job_codes: dict) -> dict:
    """Translate military code to VWC development path."""
    # Clean and standardize input
    code = code.upper().strip()
    
    # Remove common prefixes if provided
    prefixes = ["MOS", "AFSC", "RATE"]
    for prefix in prefixes:
        if code.startswith(prefix):
            code = code.replace(prefix, "").strip()
    
    # Try different prefix combinations
    possible_codes = [
        f"MOS_{code}",
        f"AFSC_{code}",
        f"RATE_{code}"
    ]
    
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
    
    # Default response for unknown codes
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

def get_chat_response(messages: List[Dict]) -> str:
    """Get response from OpenAI chat completion."""
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except openai.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat completion: {e}")
        raise

def export_chat_history(chat_history: List[Dict]) -> str:
    """Export chat history to JSON."""
    export_data = {
        "timestamp": datetime.now().isoformat(),
        "messages": chat_history
    }
    return json.dumps(export_data, indent=2)

def save_feedback(feedback: Dict):
    """Save user feedback to file."""
    feedback_dir = "feedback"
    os.makedirs(feedback_dir, exist_ok=True)
    
    feedback_file = os.path.join(
        feedback_dir,
        f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    
    with open(feedback_file, 'w') as f:
        json.dump(feedback, f, indent=2)

def handle_command(command: str) -> str:
    """Handle special commands including MOS translation."""
    parts = command.lower().split()
    if not parts:
        return None
        
    cmd = parts[0]
    if cmd in ['/mos', '/afsc', '/rate']:
        if len(parts) < 2:
            return "Please provide a military job code. Example: `/mos 25B`"
            
        code = parts[1]
        translation = translate_military_code(code, st.session_state.job_codes)
        if translation['found']:
            return (
                f"🎖️ **{translation['data']['title']}** ({translation['data']['branch']})\n\n"
                f"💻 **VWC Development Path**: {translation['data']['dev_path']}\n\n"
                "🔧 **Military Skills**:\n" +
                "\n".join(f"- {skill}" for skill in translation['data']['skills']) +
                "\n\n📚 **VWC Tech Focus**:\n" +
                "\n".join(f"{i+1}. {focus}" for i, focus in enumerate(translation['data']['tech_focus']))
            )
        else:
            return (
                "I don't have that specific code in my database, but here's a recommended "
                "VWC learning path based on general military experience:\n\n" +
                "\n".join(f"{i+1}. {focus}" for i, focus in enumerate(translation['data']['tech_focus']))
            )
    
    return None

def initialize_chat():
    """Initialize the chat with a VWC-focused welcome message."""
    welcome_message = {
        "role": "assistant",
        "content": (
            "Welcome to VetsAI - Your Vets Who Code Assistant! 👨‍💻\n\n"
            "I'm here to help you with:\n\n"
            "🔹 VWC Tech Stack:\n"
            "- JavaScript/TypeScript\n"
            "- Python (FastAPI, Flask, Django)\n"
            "- Next.js & Tailwind CSS\n"
            "- AI/ML Integration\n\n"
            "🔹 Commands:\n"
            "- `/mos [code]` - Translate your MOS to dev path\n"
            "- `/afsc [code]` - Translate your AFSC to dev path\n"
            "- `/rate [code]` - Translate your Rate to dev path\n"
            "- `/frontend` - Help with JS/TS/Next.js\n"
            "- `/backend` - Help with Python frameworks\n"
            "- `/ai` - AI/ML guidance\n\n"
            "Let's start by checking how your military experience "
            "aligns with software development! Share your MOS/AFSC/Rate, "
            "or ask about any part of our tech stack."
        )
    }
    return [welcome_message]

def main():
    """Main application function."""
    st.title("🇺🇸 VetsAI: Vets Who Code Assistant")
    
    # Initialize session
    if 'session_id' not in st.session_state:
        st.session_state.session_id = hashlib.md5(
            str(time.time()).encode()
        ).hexdigest()
    
    # Load military job codes
    if 'job_codes' not in st.session_state:
        try:
            st.session_state.job_codes = load_military_job_codes()
        except Exception as e:
            logger.error(f"Error loading job codes: {e}")
            st.session_state.job_codes = {}
    
    if 'messages' not in st.session_state:
        st.session_state.messages = initialize_chat()
    
    # Add sidebar with VWC tech stack resources
    with st.sidebar:
        st.markdown("""
        ### VWC Tech Stack
        
        🌐 **Frontend**
        - JavaScript/TypeScript
        - CSS & Tailwind
        - Next.js
        
        ⚙️ **Backend**
        - Python
        - FastAPI
        - Flask
        - Django
        
        🤖 **AI/ML Integration**
        - Machine Learning
        - AI Applications
        
        🎖️ **Military Translation**
        `/mos [code]` - Army/Marines
        `/afsc [code]` - Air Force
        `/rate [code]` - Navy/Coast Guard
        """)
    
    # Chat interface
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input():
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Check for commands first
        if prompt.startswith('/'):
            command_response = handle_command(prompt)
            if command_response:
                with st.chat_message("assistant"):
                    st.markdown(command_response)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": command_response
                })
                return
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            try:
                messages = st.session_state.messages.copy()
                messages.insert(0, {
                    "role": "system",
                    "content": (
                        "You are a specialized AI assistant for Vets Who Code troops. "
                        "Focus specifically on our tech stack: JavaScript, TypeScript, "
                        "Python, CSS, Tailwind, FastAPI, Flask, Next.js, Django, and AI/ML. "
                        "Always reference these specific technologies in your answers. "
                        "Remember all users are VWC troops learning our stack."
                    )
                })
                
                response = get_chat_response(messages)
                st.markdown(response)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })
            except Exception as e:
                st.error(f"Error generating response: {str(e)}")
    
    # Export chat history
    if st.button("Export Chat History"):
        chat_export = export_chat_history(st.session_state.messages)
        st.download_button(
            "Download Chat History",
            chat_export,
            "vetsai_chat_history.json",
            "application/json"
        )
    
    # Feedback mechanism
    with st.expander("Provide Feedback"):
        feedback_rating = st.slider(
            "Rate your experience (1-5)",
            min_value=1,
            max_value=5,
            value=5
        )
        feedback_text = st.text_area("Additional feedback")
        
        if st.button("Submit Feedback"):
            feedback = {
                "timestamp": datetime.now().isoformat(),
                "session_id": st.session_state.session_id,
                "rating": feedback_rating,
                "feedback": feedback_text
            }
            save_feedback(feedback)
            st.success("Thank you for your feedback!")

if __name__ == "__main__":
    main()
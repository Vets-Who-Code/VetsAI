import streamlit as st
import os
import logging
from typing import Dict, List
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import json
import time
import hashlib

# Configure page settings and styling
st.set_page_config(
    page_title="🇺VetsAI: Vets Who Code Assistant",
    page_icon="🇺🇸",
    layout="wide",
)

# Define VWC brand colors and add custom CSS
st.markdown("""
    <style>
    /* VWC Brand Colors */
    :root {
        --navy-blue: #091f40;
        --red: #c5203e;
        --white: #ffffff;
    }
    
    /* Sidebar styles */
    [data-testid="stSidebarUserContent"] {
        color: var(--white) !important;
    }
    
    [data-testid="stSidebarUserContent"] .stMarkdown {
        color: var(--white) !important;
    }
    
    /* Make sidebar headers and text white */
    [data-testid="stSidebarUserContent"] h1,
    [data-testid="stSidebarUserContent"] h2,
    [data-testid="stSidebarUserContent"] h3,
    [data-testid="stSidebarUserContent"] h4,
    [data-testid="stSidebarUserContent"] h5,
    [data-testid="stSidebarUserContent"] h6,
    [data-testid="stSidebarUserContent"] p,
    [data-testid="stSidebarUserContent"] li {
        color: var(--white) !important;
    }
    
    /* Style strong tags in sidebar */
    [data-testid="stSidebarUserContent"] strong {
        color: var(--white) !important;
    }

        code {
        font-family: "Source Code Pro", monospace;
        padding: 0.2em 0.4em;
        margin: 0px;
        border-radius: 0.25rem;
        background: rgb(--navy-blue);
        color: var(--white) !important;
        overflow-wrap: break-word;
    }

       /* Style chat input text color */
    .stTextInput input, .stTextInput textarea {
        color: white !important;
    }
    
    /* Style placeholder text color */
    .stTextInput input::placeholder, .stTextInput textarea::placeholder {
        color: rgba(255, 255, 255, 0.6) !important;
    }
    </style>
""", unsafe_allow_html=True)

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

# Optionally, load the model name if needed
client = OpenAI(api_key=st.secrets["openai"]["OPENAI_API_KEY"])

# Test the setup
if not client.api_key:  # Changed from openai.api_key to client.api_key
    raise ValueError("OpenAI API key not found in Streamlit secrets.")

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
        "information_technology": ["technology", "computer", "network", "data", "software", "hardware", "system", "database"],
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

def get_chat_response(messages: List[Dict]) -> str:
    """Get response from OpenAI chat completion."""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
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
            "- Python (FastAPI, Streamlit)\n"
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
        st.session_state.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()
    
    if 'job_codes' not in st.session_state:
        try:
            st.session_state.job_codes = load_military_job_codes()
        except Exception as e:
            logger.error(f"Error loading job codes: {e}")
            st.session_state.job_codes = {}
    
    if 'messages' not in st.session_state:
        st.session_state.messages = initialize_chat()
    
    # Sidebar with VWC tech stack resources
    with st.sidebar:
        st.markdown("""
### VWC Tech Stack

#### 🌐 Frontend
- **JavaScript/TypeScript**: For building scalable, maintainable codebases.
- **CSS & Tailwind CSS**: For styling and responsive design.
- **Next.js**: React framework for server-side rendering and static web applications.

#### ⚙️ Backend
- **Python**: Core language for backend development and data processing.
- **FastAPI**: For building fast, asynchronous APIs with Python.
- **Streamlit**: Framework for creating data-driven apps and interactive visualizations in Python.

#### 🤖 AI/ML Integration
- **Machine Learning (ML)**: Tools and frameworks for model development.
- **AI Applications**: Integrating AI models and APIs in applications, including OpenAI GPT models.

#### 📊 Data & Visualization
- **Pandas**: Data manipulation and analysis.
- **Matplotlib & Plotly**: Data visualization libraries for generating plots and charts.

#### 🛠️ DevOps and Tooling
- **Git & GitHub**: Version control and collaborative code management.
- **Docker**: Containerization for consistent development and deployment.
- **VS Code**: Development environment setup with extensions for Python, JavaScript, etc.

#### 🧪 Testing
- **Jest**: JavaScript testing framework for frontend applications.
- **Pytest**: Testing framework for Python applications, with extensive plugin support.
- **Coverage.py**: For measuring code coverage in Python projects.

""", unsafe_allow_html=True)

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Check for commands
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
                        "You are a specialized AI assistant for Vets Who Code members, designed to provide clear, practical technical guidance "
                        "to veterans transitioning into software development careers.\n\n"
                        
                        "CORE TECH STACK:\n"
                        "- Frontend: JavaScript, TypeScript, React, Next.js\n"
                        "- Styling: CSS, Tailwind CSS\n"
                        "- Backend: Python, FastAPI\n"
                        "- Data & Visualization: Streamlit\n"
                        "- Advanced: AI/ML fundamentals\n"
                        "- Development Tools: Git, GitHub, VS Code\n"
                        "- Testing: Jest, Pytest\n\n"
                        
                        "CAREER TRANSITION GUIDANCE:\n"
                        "1. Resume Development:\n"
                        "   - Technical Skills: Programming Languages, Frameworks, Tools, Cloud, Testing\n"
                        "   - Military Experience Translation: Leadership, Problem-solving, Team Collaboration\n\n"
                        
                        "2. Portfolio Development:\n"
                        "   - Clean code and documentation\n"
                        "   - Version control and API integration\n"
                        "   - Responsive design and performance\n"
                        "   - Testing and TypeScript implementation\n"
                        "   - Security and accessibility standards\n\n"
                        
                        "LEARNING PATHS:\n"
                        "1. Fundamentals: HTML, CSS, JavaScript, Git\n"
                        "2. Intermediate: TypeScript, React, Python\n"
                        "3. Advanced: Next.js, FastAPI, Streamlit, AI/ML\n\n"
                        
                        "PROJECT FOCUS:\n"
                        "1. Portfolio Projects: Personal website, APIs, Data visualization\n"
                        "2. Technical Skills: Code quality, Testing, Security, Performance\n"
                        "3. Career Materials: GitHub profile, Technical blog, Documentation\n\n"
                        
                        "Remember: Provide practical guidance for building technical skills and transitioning to software development careers. "
                        "Focus on concrete examples and best practices."
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
        st.download_button("Download Chat History", chat_export, "vetsai_chat_history.json", "application/json")

    # Feedback mechanism
    with st.expander("Provide Feedback"):
        feedback_rating = st.slider("Rate your experience (1-5)", min_value=1, max_value=5, value=5)
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
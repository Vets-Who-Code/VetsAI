import streamlit as st
import os
import httpx
import nest_asyncio
from better_profanity import profanity
from PyPDF2 import PdfReader
import docx
from dotenv import load_dotenv

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Initialize the better-profanity filter
profanity.load_censor_words()

# Load the environment variables from .env file
load_dotenv()

# Get the API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Function to inject custom CSS for light mode
def inject_custom_css():
    st.markdown("""
        <!-- Your existing CSS styles -->
    """, unsafe_allow_html=True)

inject_custom_css()

# Function to read and extract text from PDFs
def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

# Function to read and extract text from Word documents
def extract_text_from_word(file):
    doc = docx.Document(file)
    return "\n".join([paragraph.text for paragraph in doc.paragraphs])

# Function to load military job codes from the directories (TXT format)
def load_military_job_codes(base_path):
    # Your existing implementation
    pass

# Function to translate military job code to civilian job suggestions
def translate_job_code(job_code, job_codes):
    # Your existing implementation
    pass

# Fetch response from OpenAI using the API key with increased timeout
def fetch_from_model(conversation):
    """Send a request to OpenAI using the conversation history."""
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o",  # Use 'gpt-3.5-turbo' or 'gpt-4' if available
        "messages": conversation,
        "temperature": 0.7,
        "max_tokens": 5000
    }

    try:
        # Set a custom timeout (e.g., 60 seconds) to give more time for OpenAI to respond
        response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()

        json_response = response.json()
        return json_response['choices'][0]['message']['content']

    except httpx.TimeoutException:
        st.error("The request to OpenAI timed out. Please try again later.")
        return "Timeout occurred while waiting for OpenAI response."

    except httpx.RequestError as e:
        st.error(f"An error occurred while making a request to OpenAI: {e}")
        return "Error communicating with the OpenAI API."
    
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return "Unexpected error while fetching response."

# Callback to process user input and clear it afterward
def process_input(job_codes):
    user_input = st.session_state["temp_input"]
    
    if user_input:
        # Store user input into chat history
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Build conversation history for OpenAI API call
        conversation = [{"role": "system", "content": "You are a helpful assistant for veterans seeking employment."}]

        # Include document content in the system prompt if available
        if "document_content" in st.session_state and st.session_state["document_content"]:
            conversation[0]["content"] += f" The user has provided the following document content to assist you: {st.session_state['document_content']}"

        # Append previous messages, being mindful of token limits
        for msg in st.session_state.messages[-10:]:  # Adjust the number of messages as needed
            conversation.append(msg)

        # Fetch assistant's response
        response = fetch_from_model(conversation)

        # Store assistant's response
        st.session_state.messages.append({"role": "assistant", "content": response})

    # Clear the temporary input
    st.session_state["temp_input"] = ""

# Handle user input and job code translation along with resume upload
def handle_user_input(job_codes):
    """Handle user input for translating military job codes to civilian jobs, uploading resumes, and chatting."""
    
    # Display chat messages first
    display_chat_messages()

    # File uploader for document uploads
    uploaded_file = st.file_uploader("Upload your employment-related document (PDF, DOCX)", type=["pdf", "docx"])

    if uploaded_file is not None:
        file_text = ""
        
        if uploaded_file.type == "application/pdf":
            file_text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            file_text = extract_text_from_word(uploaded_file)

        # Store the extracted content in session state
        st.session_state["document_content"] = file_text

        st.success("Document uploaded and processed successfully!")

    # Input field for user queries (job code or general chat) at the bottom
    st.text_input("Enter your military job code (e.g., 11B, AFSC, MOS) or ask a question:", 
                  key="temp_input", 
                  on_change=process_input, 
                  args=(job_codes,))

# Display the app title and description
def display_title_and_description():
    """Display the app title and description."""
    st.title("🇺🇸 VetsAI: Employment Assistance for Veterans")
    st.write(
        "Welcome to VetsAI, an AI-powered virtual assistant designed "
        "to help veterans navigate employment transitions and find opportunities in civilian careers."
    )

# Initialize session state
def initialize_session_state():
    """Initialize session state variables for messages and chat history."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "temp_input" not in st.session_state:
        st.session_state.temp_input = ""
    if "document_content" not in st.session_state:
        st.session_state.document_content = ""

# Introduce the assistant
def introduce_assistant():
    """Introduce the VetsAI Assistant."""
    if not st.session_state.messages:
        intro_message = (
            "Hi, I'm VetsAI! I'm here to assist you in finding employment opportunities and transitioning into civilian careers. "
            "Feel free to ask me anything related to job searching, resume tips, or industries that align with your skills."
        )
        st.session_state.messages.append({"role": "assistant", "content": intro_message})

# Display chat history
def display_chat_messages():
    """Display existing chat messages stored in session state."""
    for message in st.session_state["messages"]:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(f"You: {message['content']}")
        else:
            with st.chat_message("assistant"):
                st.markdown(f"VetsAI: {message['content']}")

# Main function to run the VetsAI Assistant app
def main():
    """Main function to run the VetsAI Assistant app."""
    display_title_and_description()
    initialize_session_state()

    # Load the military job codes from the 'data/employment_transitions/job_codes' directory
    job_codes = load_military_job_codes("./data/employment_transitions/job_codes")

    # Ensure the assistant introduces itself only once
    introduce_assistant()

    # Handle user input and chat
    handle_user_input(job_codes)

if __name__ == "__main__":
    main()

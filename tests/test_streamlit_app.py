import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, mock_open, MagicMock, call
import json
import openai
from datetime import datetime

# Get the absolute path to the project root directory
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from app import (
    load_military_job_codes,
    map_to_vwc_path,
    translate_military_code,
    get_chat_response,
    handle_command,
    export_chat_history,
    save_feedback,
    parse_mos_file
)

# Sample text content
SAMPLE_MOS_TEXT = """
Job Code: 25B

Description:
Manages or supervises a specific automated system or node in a data or communications network.

Manages or supervises a specific automated system or node in a data or communications network supporting tactical, theater, strategic or base operations; provides detailed technical direction and advice to commanders, staffs and other Command, Control, and Communications (C3) users at all echelons on the installation, operation and maintenance of distributed operating and data base systems, teleprocessing systems, and data communications supporting Battlefield Automated Systems (BAS); requires the practical application of automation theory to the design, implementation and successful interoperation of hardware and software for automated telecommunications and teleprocessing systems.
"""

@pytest.fixture
def mock_job_codes():
    return {
        "MOS_25B": {
            "title": "Information Technology Specialist",
            "branch": "army",
            "category": "information_technology",
            "skills": ["Network administration", "System maintenance"],
            "vwc_path": "Full Stack Development",
            "tech_focus": [
                "JavaScript/TypeScript with focus on system architecture",
                "Next.js for complex web applications",
                "Python backend services with FastAPI"
            ],
            "code_type": "MOS"
        }
    }

@patch("os.path.join", lambda *args: "/".join(args))
@patch("builtins.open", new_callable=mock_open)
def test_load_military_job_codes(mock_file):
    # Setup mock file content
    mock_file.return_value.__enter__.return_value.read.return_value = SAMPLE_MOS_TEXT

    def mock_exists(path):
        return True

    def mock_listdir(path):
        if path.endswith("job_codes"):
            return ["army", "air_force", "navy", "marine_corps", "coast_guard"]
        else:
            return ["25B.txt"]

    with patch("os.path.exists", side_effect=mock_exists), \
         patch("os.listdir", side_effect=mock_listdir):
        
        job_codes = load_military_job_codes()
        
        # Basic validations
        assert isinstance(job_codes, dict)
        assert len(job_codes) > 0
        
        # Verify the structure
        for key, value in job_codes.items():
            assert isinstance(value, dict)
            assert "title" in value
            assert "branch" in value
            assert "skills" in value
            assert isinstance(value["skills"], list)
        
        # Verify that mock_file was called
        assert mock_file.call_count > 0

def test_parse_mos_file():
    """Test the MOS file parsing function"""
    result = parse_mos_file(SAMPLE_MOS_TEXT)
    
    # Basic structure tests
    assert isinstance(result, dict)
    assert "title" in result
    assert "category" in result
    assert "skills" in result
    assert isinstance(result["skills"], list)
    assert len(result["skills"]) > 0
    
    # Content tests
    assert result["title"].startswith("Manages or supervises")
    assert result["category"] == "information_technology"  # Should match because of network/data/system keywords
    
    # Skills check
    assert any("network" in skill.lower() for skill in result["skills"])

def test_parse_mos_file_edge_cases():
    """Test parse_mos_file with various edge cases"""
    # Empty content
    empty_result = parse_mos_file("")
    assert empty_result["title"] == "Military Professional"
    assert empty_result["category"] == "general"
    assert isinstance(empty_result["skills"], list)
    
    # Content with only job code
    job_code_only = "Job Code: 25B"
    job_code_result = parse_mos_file(job_code_only)
    assert job_code_result["title"] == "Military Professional"
    assert isinstance(job_code_result["skills"], list)
    
    # Content with special characters
    special_chars = """
    Job Code: 25B
    
    Description:
    Network & Systems Administrator (IT/IS)
    
    Manages & maintains computer networks/systems.
    """
    special_result = parse_mos_file(special_chars)
    assert special_result["category"] == "information_technology"

def test_map_to_vwc_path_it_category():
    result = map_to_vwc_path("information_technology", ["programming", "networking"])
    assert result["path"] == "Full Stack Development"
    assert len(result["tech_focus"]) > 0
    assert any("TypeScript" in focus for focus in result["tech_focus"])

def test_map_to_vwc_path_default():
    result = map_to_vwc_path("unknown_category", [])
    assert result["path"] == "Full Stack Development"
    assert len(result["tech_focus"]) > 0

def test_translate_military_code_found(mock_job_codes):
    result = translate_military_code("25B", mock_job_codes)
    assert result["found"] == True
    assert result["data"]["title"] == "Information Technology Specialist"
    assert result["data"]["branch"] == "army"

def test_translate_military_code_not_found(mock_job_codes):
    result = translate_military_code("99Z", mock_job_codes)
    assert result["found"] == False
    assert "dev_path" in result["data"]
    assert isinstance(result["data"]["tech_focus"], list)

@patch("openai.chat.completions.create")
def test_get_chat_response(mock_create):
    # Mock the OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
    mock_create.return_value = mock_response

    messages = [{"role": "user", "content": "Hello"}]
    response = get_chat_response(messages)
    assert response == "Test response"
    mock_create.assert_called_once()

def test_handle_command_mos(mock_job_codes):
    with patch("streamlit.session_state") as mock_session:
        mock_session.job_codes = mock_job_codes
        response = handle_command("/mos 25B")
        assert response is not None
        assert "Information Technology Specialist" in response
        assert "VWC Development Path" in response

def test_handle_command_invalid():
    response = handle_command("/invalid")
    assert response is None

def test_handle_command_missing_code():
    response = handle_command("/mos")
    assert "Please provide a military job code" in response

def test_export_chat_history():
    chat_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"}
    ]
    result = export_chat_history(chat_history)
    assert isinstance(result, str)
    
    # Verify JSON structure
    exported_data = json.loads(result)
    assert "timestamp" in exported_data
    assert "messages" in exported_data
    assert len(exported_data["messages"]) == 2

@patch("builtins.open", new_callable=mock_open)
@patch("os.makedirs")
def test_save_feedback(mock_makedirs, mock_file):
    feedback = {
        "rating": 5,
        "feedback": "Great service!",
        "session_id": "test123"
    }
    
    # Call the function
    save_feedback(feedback)
    
    # Verify makedirs was called
    mock_makedirs.assert_called_once()
    
    # Verify open was called with write mode
    mock_file.assert_called_once()
    
    # Get the mock file handle
    handle = mock_file()
    
    # Get what was written to the file
    written_calls = handle.write.call_args_list
    assert len(written_calls) > 0
    
    # Combine all written data
    written_data = ''.join(call[0][0] for call in written_calls)
    
    # Verify it's valid JSON
    try:
        parsed_data = json.loads(written_data)
        assert parsed_data["rating"] == 5
        assert parsed_data["feedback"] == "Great service!"
        assert parsed_data["session_id"] == "test123"
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON written to file: {written_data}")

@pytest.mark.parametrize("category,expected_path", [
    ("cyber", "Security-Focused Development"),
    ("intelligence", "AI/ML Development"),
    ("communications", "Frontend Development"),
    ("maintenance", "Backend Development"),
    ("unknown", "Full Stack Development"),
])
def test_map_to_vwc_path_categories(category, expected_path):
    result = map_to_vwc_path(category, [])
    assert result["path"] == expected_path
    assert isinstance(result["tech_focus"], list)
    assert len(result["tech_focus"]) > 0

if __name__ == "__main__":
    pytest.main(["-v"])
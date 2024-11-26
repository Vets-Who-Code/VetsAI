import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, mock_open, MagicMock, call
import json
from datetime import datetime

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

@pytest.fixture
def mock_file_system():
    def mock_exists(path):
        return True

    def mock_listdir(path):
        if path.endswith("job_codes"):
            return ["army", "air_force", "navy", "marine_corps", "coast_guard"]
        else:
            return ["25B.txt"]
    
    return {"exists": mock_exists, "listdir": mock_listdir}

class TestMilitaryJobCodes:
    @patch("os.path.join", lambda *args: "/".join(args))
    @patch("builtins.open", new_callable=mock_open)
    def test_load_military_job_codes(self, mock_file, mock_file_system):
        mock_file.return_value.__enter__.return_value.read.return_value = SAMPLE_MOS_TEXT

        with patch("os.path.exists", side_effect=mock_file_system["exists"]), \
             patch("os.listdir", side_effect=mock_file_system["listdir"]):
            
            job_codes = load_military_job_codes()
            
            assert isinstance(job_codes, dict)
            assert len(job_codes) > 0
            
            for key, value in job_codes.items():
                assert isinstance(value, dict)
                assert all(field in value for field in ["title", "branch", "skills"])
                assert isinstance(value["skills"], list)
            
            assert mock_file.call_count > 0

    def test_parse_mos_file(self):
        result = parse_mos_file(SAMPLE_MOS_TEXT)
        
        assert isinstance(result, dict)
        assert all(field in result for field in ["title", "category", "skills"])
        assert isinstance(result["skills"], list)
        assert len(result["skills"]) > 0
        
        assert "manages or supervises" in result["title"].lower()
        assert result["category"] == "information_technology"
        assert any("network" in skill.lower() for skill in result["skills"])

    @pytest.mark.parametrize("test_input,expected", [
        ("", {
            "title": "Military Professional",
            "category": "general",
            "skills": []
        }),
        ("Job Code: 25B", {
            "title": "Military Professional",
            "category": "general",
            "skills": []
        }),
        ("""Job Code: 25B
        Description:
        Network & Systems Administrator (IT/IS)
        Manages & maintains computer networks/systems.""", {
            "category": "information_technology",
            "skills": ["Network & Systems Administrator (IT/IS)", 
                      "Manages & maintains computer networks/systems."]
        })
    ])
    def test_parse_mos_file_edge_cases(self, test_input, expected):
        result = parse_mos_file(test_input)
        for key, value in expected.items():
            assert result[key] == value

class TestPathMapping:
    @pytest.mark.parametrize("category,skills,expected_path", [
        ("information_technology", ["programming", "networking"], "Full Stack Development"),
        ("cyber", [], "Security-Focused Development"),
        ("intelligence", [], "AI/ML Development"),
        ("communications", [], "Frontend Development"),
        ("maintenance", [], "Backend Development"),
        ("unknown", [], "Full Stack Development")
    ])
    def test_map_to_vwc_path(self, category, skills, expected_path):
        result = map_to_vwc_path(category, skills)
        assert result["path"] == expected_path
        assert isinstance(result["tech_focus"], list)
        assert len(result["tech_focus"]) > 0

class TestMilitaryCodeTranslation:
    def test_translate_military_code_found(self, mock_job_codes):
        result = translate_military_code("25B", mock_job_codes)
        assert result["found"] is True
        assert result["data"]["title"] == "Information Technology Specialist"
        assert result["data"]["branch"] == "army"

    def test_translate_military_code_not_found(self, mock_job_codes):
        result = translate_military_code("99Z", mock_job_codes)
        assert result["found"] is False
        assert "dev_path" in result["data"]
        assert isinstance(result["data"]["tech_focus"], list)

class TestChatFunctionality:
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"}) 
    @patch('openai.OpenAI')
    def test_get_chat_response(self, mock_openai):
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_msg = MagicMock()
        
        mock_msg.content = "Test response"
        mock_choice.message = mock_msg
        mock_completion.choices = [mock_choice]
        
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client

        messages = [{"role": "user", "content": "Hello"}]
        
        with patch('app.client', mock_client):
            response = get_chat_response(messages)
            
            assert response == "Test response"
            mock_client.chat.completions.create.assert_called_once_with(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
            )

    def test_handle_command_mos(self, mock_job_codes):
        with patch("streamlit.session_state", create=True) as mock_session:
            mock_session.job_codes = mock_job_codes
            response = handle_command("/mos 25B")
            
            assert response is not None
            assert "Information Technology Specialist" in response
            assert "VWC Development Path" in response

    @pytest.mark.parametrize("command,expected", [
        ("/invalid", None),
        ("/mos", "Please provide a military job code"),
        ("/mos  ", "Please provide a military job code")
    ])
    def test_handle_command_edge_cases(self, command, expected):
        response = handle_command(command)
        if expected is None:
            assert response is None
        else:
            assert expected in response

class TestDataManagement:
    def test_export_chat_history(self):
        chat_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"}
        ]
        result = export_chat_history(chat_history)
        
        assert isinstance(result, str)
        exported_data = json.loads(result)
        assert isinstance(exported_data["timestamp"], str)
        assert datetime.fromisoformat(exported_data["timestamp"])
        assert len(exported_data["messages"]) == 2
        assert all(msg["role"] in ["user", "assistant"] for msg in exported_data["messages"])

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_save_feedback(self, mock_makedirs, mock_file):
        feedback = {
            "rating": 5,
            "feedback": "Great service!",
            "session_id": "test123",
            "timestamp": datetime.now().isoformat()
        }
        
        save_feedback(feedback)
        
        mock_makedirs.assert_called_once()
        mock_file.assert_called_once()
        
        written_data = ''.join(call[0][0] for call in mock_file().write.call_args_list)
        parsed_data = json.loads(written_data)
        
        assert parsed_data["rating"] == 5
        assert parsed_data["feedback"] == "Great service!"
        assert parsed_data["session_id"] == "test123"
        assert isinstance(parsed_data.get("timestamp"), str)

if __name__ == "__main__":
    pytest.main(["-v"])
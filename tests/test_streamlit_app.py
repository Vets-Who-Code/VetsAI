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
    get_chat_response,
    handle_command,
    export_chat_history,
    save_feedback
)


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


class TestChatFunctionality:
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

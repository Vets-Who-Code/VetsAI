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


if __name__ == "__main__":
    pytest.main(["-v"])

import pytest
from unittest.mock import patch, mock_open

from data.data_loader import (
    load_military_job_codes,
    map_to_vwc_path,
    translate_military_code,
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


if __name__ == "__main__":
    pytest.main(["-v"])

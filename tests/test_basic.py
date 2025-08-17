"""
Basic tests to verify the testing setup works correctly.
"""

import pytest
import sys
from pathlib import Path

# Add the project root to the path so we can import our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_python_version():
    """Test that we're running Python 3.12+"""
    assert sys.version_info >= (3, 12), f"Python 3.12+ required, got {sys.version_info}"


def test_basic_math():
    """A simple test to verify pytest is working"""
    assert 2 + 2 == 4
    assert 10 / 2 == 5.0


def test_import_agent_modules():
    """Test that we can import our main agent modules"""
    try:
        # Test importing some of the main agent files
        from agent import level_1_agent
        from agent import level_2_agent
        from agent import research_agent
        
        # If we get here without ImportError, the imports worked
        assert True
        
    except ImportError as e:
        pytest.fail(f"Failed to import agent modules: {e}")


def test_project_structure():
    """Test that essential project files exist"""
    project_root = Path(__file__).parent.parent
    
    # Check for essential files
    assert (project_root / "pyproject.toml").exists()
    assert (project_root / "README.md").exists()
    assert (project_root / "agent").is_dir()
    assert (project_root / "playground").is_dir()


class TestAgentBasics:
    """Test class for basic agent functionality"""
    
    def test_agent_directory_structure(self):
        """Test that the agent directory has expected structure"""
        project_root = Path(__file__).parent.parent
        agent_dir = project_root / "agent"
        
        # Check for main agent files
        expected_files = [
            "level_1_agent.py",
            "level_2_agent.py", 
            "level_3_agent.py",
            "level_4_team.py",
            "level_5_workflow.py",
            "research_agent.py"
        ]
        
        for file_name in expected_files:
            assert (agent_dir / file_name).exists(), f"Missing agent file: {file_name}"
    
    def test_tool_directory_exists(self):
        """Test that the tool directory exists with expected tools"""
        project_root = Path(__file__).parent.parent
        tool_dir = project_root / "agent" / "tool"
        
        assert tool_dir.is_dir(), "Tool directory should exist"
        
        # Check for some expected tool files
        expected_tools = [
            "web_search.py",
            "hackernews_topstory.py"
        ]
        
        for tool_name in expected_tools:
            assert (tool_dir / tool_name).exists(), f"Missing tool: {tool_name}"

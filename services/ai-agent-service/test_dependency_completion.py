"""
Test Enhanced Dependency Completion Logic

Test that the complete_external_dependencies function properly
completes all required fields for external dependencies.
"""

import pytest
from app.agents.developer.planner.nodes.generate_plan import (
    complete_external_dependencies,
)


def test_complete_external_dependencies_with_minimal_input():
    """Test completing dependencies with minimal input fields."""
    input_deps = [
        {
            "package": "python-jose",
            "version": ">=3.3.0",
        }
    ]

    result = complete_external_dependencies(input_deps)

    assert len(result) == 1
    dep = result[0]

    # Check all required fields are present
    required_fields = [
        "package",
        "version",
        "purpose",
        "already_installed",
        "installation_method",
        "install_command",
        "package_file",
        "section",
    ]
    for field in required_fields:
        assert field in dep, f"Missing field: {field}"
        assert dep[field] is not None, f"Field {field} is None"
        assert dep[field] != "", f"Field {field} is empty string"

    # Check specific values
    assert dep["package"] == "python-jose"
    assert dep["version"] == ">=3.3.0"
    assert dep["installation_method"] == "pip"
    assert "python-jose>=3.3.0" in dep["install_command"]
    assert dep["package_file"] == "pyproject.toml"
    assert dep["section"] == "dependencies"


def test_complete_external_dependencies_with_full_input():
    """Test completing dependencies with all fields provided."""
    input_deps = [
        {
            "package": "passlib[bcrypt]",
            "version": ">=1.7.4",
            "purpose": "Password hashing with bcrypt",
            "already_installed": False,
            "installation_method": "pip",
            "package_file": "pyproject.toml",
            "section": "dependencies",
        }
    ]

    result = complete_external_dependencies(input_deps)

    assert len(result) == 1
    dep = result[0]

    assert dep["package"] == "passlib[bcrypt]"
    assert dep["version"] == ">=1.7.4"
    assert dep["purpose"] == "Password hashing with bcrypt"
    assert dep["already_installed"] is False
    assert dep["install_command"] == "pip install passlib[bcrypt]>=1.7.4"


def test_complete_external_dependencies_already_installed():
    """Test completing dependencies marked as already installed."""
    input_deps = [
        {
            "package": "fastapi",
            "version": ">=0.100.0",
            "already_installed": True,
        }
    ]

    result = complete_external_dependencies(input_deps)

    assert len(result) == 1
    dep = result[0]

    assert dep["already_installed"] is True
    assert dep["install_command"] == "Already installed"


def test_complete_external_dependencies_version_formatting():
    """Test that version constraints are properly formatted."""
    input_deps = [
        {"package": "pytest", "version": "7.0.0"},  # No operator
        {"package": "black", "version": ">=22.0.0"},  # Already has operator
        {"package": "mypy", "version": "~1.0.0"},  # Tilde operator
    ]

    result = complete_external_dependencies(input_deps)

    assert len(result) == 3

    # First should get >= prefix
    assert "pytest>=7.0.0" in result[0]["install_command"]

    # Second should keep >=
    assert "black>=22.0.0" in result[1]["install_command"]

    # Third should keep ~
    assert "mypy~1.0.0" in result[2]["install_command"]


def test_complete_external_dependencies_multiple_packages():
    """Test completing multiple dependencies with mixed information."""
    input_deps = [
        {
            "package": "python-jose[cryptography]",
            "version": ">=3.3.0",
            "purpose": "JWT token generation",
        },
        {
            "package": "passlib[bcrypt]",
            "version": ">=1.7.4",
            "purpose": "Password hashing",
            "already_installed": True,
        },
        {
            "package": "python-multipart",
            "version": ">=0.0.5",
            "purpose": "Form data parsing",
            "section": "devDependencies",
        },
    ]

    result = complete_external_dependencies(input_deps)

    assert len(result) == 3

    # Check first dependency
    assert result[0]["package"] == "python-jose[cryptography]"
    assert "python-jose[cryptography]>=3.3.0" in result[0]["install_command"]
    assert result[0]["section"] == "dependencies"

    # Check second dependency (already installed)
    assert result[1]["already_installed"] is True
    assert result[1]["install_command"] == "Already installed"

    # Check third dependency (devDependencies)
    assert result[2]["section"] == "devDependencies"
    assert "python-multipart>=0.0.5" in result[2]["install_command"]


def test_complete_external_dependencies_empty_list():
    """Test completing an empty dependency list."""
    result = complete_external_dependencies([])
    assert result == []


def test_complete_external_dependencies_missing_package_name():
    """Test handling of missing package name."""
    input_deps = [{"version": ">=1.0.0"}]

    result = complete_external_dependencies(input_deps)

    assert len(result) == 1
    dep = result[0]

    # Should have default package name
    assert dep["package"] == "unknown-package"
    assert "unknown-package" in dep["install_command"]


def test_complete_external_dependencies_install_command_format():
    """Test that install commands are properly formatted and executable."""
    input_deps = [
        {
            "package": "python-jose[cryptography]",
            "version": ">=3.3.0",
            "installation_method": "pip",
        },
        {
            "package": "jsonwebtoken",
            "version": "^9.0.0",
            "installation_method": "npm",
        },
    ]

    result = complete_external_dependencies(input_deps)

    # Check pip command
    assert result[0]["install_command"] == "pip install python-jose[cryptography]>=3.3.0"

    # Check npm command
    assert result[1]["install_command"] == "npm install jsonwebtoken^9.0.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


"""Tests for docker-compose configuration validation.

This module tests the docker-compose.yml configuration to ensure:
- All required services are defined
- Service dependencies are correctly configured
- Environment variables are properly set up
- Health checks are defined for critical services
- Networks and volumes are configured correctly
"""

import re
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def docker_compose_path() -> Path:
    """Path to the docker-compose.yml file."""
    return Path(__file__).parent.parent / "docker-compose.yml"


@pytest.fixture
def docker_compose_config(docker_compose_path: Path) -> dict:
    """Load and parse docker-compose.yml."""
    with open(docker_compose_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def env_example_path() -> Path:
    """Path to the .env.example file."""
    return Path(__file__).parent.parent / ".env.example"


class TestDockerComposeStructure:
    """Test docker-compose.yml structure and configuration."""

    def test_docker_compose_file_exists(self, docker_compose_path: Path) -> None:
        """Verify docker-compose.yml exists."""
        assert docker_compose_path.exists(), "docker-compose.yml not found"

    def test_docker_compose_is_valid_yaml(self, docker_compose_config: dict) -> None:
        """Verify docker-compose.yml is valid YAML."""
        assert docker_compose_config is not None
        assert isinstance(docker_compose_config, dict)

    def test_all_required_services_defined(self, docker_compose_config: dict) -> None:
        """Verify all required services are defined."""
        services = docker_compose_config.get("services", {})
        required_services = ["db", "api", "worker", "frontend"]

        for service in required_services:
            assert service in services, f"Service '{service}' not defined"

    def test_database_service_configuration(self, docker_compose_config: dict) -> None:
        """Verify database service is properly configured."""
        db = docker_compose_config["services"]["db"]

        # Check image
        assert "postgres" in db["image"].lower()

        # Check environment variables
        env = db["environment"]
        assert "POSTGRES_DB" in env
        assert "POSTGRES_USER" in env
        assert "POSTGRES_PASSWORD" in env

        # Check health check
        assert "healthcheck" in db
        assert "test" in db["healthcheck"]

        # Check volume mounting
        assert "volumes" in db
        assert any("postgresql/data" in str(v) for v in db["volumes"])

    def test_api_service_configuration(self, docker_compose_config: dict) -> None:
        """Verify API service is properly configured."""
        api = docker_compose_config["services"]["api"]

        # Check build configuration
        assert "build" in api
        assert api["build"]["target"] == "api"

        # Check dependencies
        assert "depends_on" in api
        assert "db" in api["depends_on"]

        # Check health check
        assert "healthcheck" in api

        # Check port exposure
        assert "ports" in api

        # Check environment includes required vars
        env = api["environment"]
        assert "DATABASE_URL" in env
        assert "OPENAI_API_KEY" in env

    def test_worker_service_configuration(self, docker_compose_config: dict) -> None:
        """Verify worker service is properly configured."""
        worker = docker_compose_config["services"]["worker"]

        # Check build configuration
        assert "build" in worker
        assert worker["build"]["target"] == "worker"

        # Check dependencies
        assert "depends_on" in worker
        deps = worker["depends_on"]
        assert "db" in deps or "db" in [d for d in deps if isinstance(d, str)]

        # Check environment includes required vars
        env = worker["environment"]
        assert "DATABASE_URL" in env
        assert "OPENAI_API_KEY" in env

    def test_frontend_service_configuration(self, docker_compose_config: dict) -> None:
        """Verify frontend service is properly configured."""
        frontend = docker_compose_config["services"]["frontend"]

        # Check build configuration
        assert "build" in frontend

        # Check it depends on API
        assert "depends_on" in frontend
        assert "api" in frontend["depends_on"]

        # Check profiles (frontend is optional)
        assert "profiles" in frontend
        assert "frontend" in frontend["profiles"]

    def test_volumes_defined(self, docker_compose_config: dict) -> None:
        """Verify required volumes are defined."""
        volumes = docker_compose_config.get("volumes", {})
        required_volumes = ["postgres_data", "upload_data"]

        for volume in required_volumes:
            assert volume in volumes, f"Volume '{volume}' not defined"

    def test_network_defined(self, docker_compose_config: dict) -> None:
        """Verify network is defined."""
        networks = docker_compose_config.get("networks", {})
        assert "vtt-network" in networks

    def test_all_services_use_network(self, docker_compose_config: dict) -> None:
        """Verify all services are connected to the network."""
        services = docker_compose_config["services"]

        for service_name, service in services.items():
            assert "networks" in service, f"Service '{service_name}' not connected to network"
            assert "vtt-network" in service["networks"]


class TestEnvExampleFile:
    """Test .env.example file configuration."""

    def test_env_example_exists(self, env_example_path: Path) -> None:
        """Verify .env.example exists."""
        assert env_example_path.exists(), ".env.example not found"

    def test_env_example_has_required_vars(self, env_example_path: Path) -> None:
        """Verify all required environment variables are documented."""
        with open(env_example_path) as f:
            content = f.read()

        required_vars = [
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "OPENAI_API_KEY",
            "SECRET_KEY",
            "DATABASE_URL",  # Should be in comments/examples
        ]

        for var in required_vars:
            assert var in content, f"Required variable '{var}' not in .env.example"

    def test_env_example_has_security_warnings(self, env_example_path: Path) -> None:
        """Verify security warnings are present."""
        with open(env_example_path) as f:
            content = f.read()

        # Check for REQUIRED warnings and security guidance
        assert "REQUIRED" in content, "Missing REQUIRED variable indicators"
        assert "secure" in content.lower(), "Missing security guidance"

    def test_env_example_structure(self, env_example_path: Path) -> None:
        """Verify .env.example has proper structure."""
        with open(env_example_path) as f:
            content = f.read()

        # Should have section headers (comments with separators)
        assert re.search(r"#.*={3,}", content), "Missing section headers"

        # Should have variable assignments
        assert re.search(r"^\w+=", content, re.MULTILINE), "Missing variable assignments"


class TestDockerfileTargets:
    """Test Dockerfile multi-stage build targets."""

    def test_dockerfile_exists(self) -> None:
        """Verify Dockerfile exists."""
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        assert dockerfile.exists(), "Dockerfile not found"

    def test_dockerfile_has_required_targets(self) -> None:
        """Verify Dockerfile has all required build targets."""
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        with open(dockerfile) as f:
            content = f.read()

        required_targets = ["builder", "base", "cli", "api", "worker"]

        for target in required_targets:
            pattern = rf"FROM .+ AS {target}"
            assert re.search(pattern, content), f"Target '{target}' not found in Dockerfile"

    def test_api_target_exposes_port(self) -> None:
        """Verify API target exposes port 8000."""
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        with open(dockerfile) as f:
            content = f.read()

        # Find API section
        api_section = re.search(r"FROM base AS api.*?(?=FROM|\Z)", content, re.DOTALL)
        assert api_section, "API target not found"

        # Check for EXPOSE command
        assert "EXPOSE 8000" in api_section.group()

    def test_worker_target_has_cmd(self) -> None:
        """Verify worker target has proper CMD."""
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        with open(dockerfile) as f:
            content = f.read()

        # Find worker section
        worker_section = re.search(r"FROM base AS worker.*?(?=FROM|\Z)", content, re.DOTALL)
        assert worker_section, "Worker target not found"

        # Check for CMD
        assert "CMD" in worker_section.group()


class TestDatabaseInitScript:
    """Test database initialization script."""

    def test_init_script_exists(self) -> None:
        """Verify database init script exists."""
        init_script = Path(__file__).parent.parent / "docker" / "init-db.sql"
        assert init_script.exists(), "docker/init-db.sql not found"

    def test_init_script_creates_tables(self) -> None:
        """Verify init script creates required tables."""
        init_script = Path(__file__).parent.parent / "docker" / "init-db.sql"
        with open(init_script) as f:
            content = f.read()

        required_tables = ["users", "transcription_jobs", "api_keys"]

        for table in required_tables:
            # Use regex to match CREATE TABLE statements for this specific table
            # Pattern matches: CREATE TABLE [IF NOT EXISTS] [schema.]table_name
            pattern = rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\w+\.)?{re.escape(table)}\b"
            assert re.search(pattern, content, re.IGNORECASE), f"CREATE TABLE statement not found for table '{table}'"

    def test_init_script_creates_indices(self) -> None:
        """Verify init script creates database indices."""
        init_script = Path(__file__).parent.parent / "docker" / "init-db.sql"
        with open(init_script) as f:
            content = f.read()

        assert "CREATE INDEX" in content, "No indices created"

    def test_init_script_has_no_default_user(self) -> None:
        """Verify init script does NOT create default admin user (security requirement)."""
        init_script = Path(__file__).parent.parent / "docker" / "init-db.sql"
        with open(init_script) as f:
            content = f.read()

        # Security: No default admin user should be created
        assert "INSERT INTO users" not in content, "Default user should not be created for security"
        assert "Create users via the API" in content or "manually via psql" in content, (
            "Should have user creation instructions"
        )

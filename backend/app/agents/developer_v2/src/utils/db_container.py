"""Database container management using testcontainers."""
import os
import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)
_postgres_container = None


def start_postgres_container() -> Dict[str, str]:
    """Start a postgres container and return connection info."""
    global _postgres_container
    
    if _postgres_container is not None:
        return get_connection_info()
    
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        logger.warning("[db_container] testcontainers not installed")
        return {}
    
    logger.info("[db_container] Starting postgres container...")
    _postgres_container = PostgresContainer("postgres:16")
    _postgres_container.start()
    
    info = get_connection_info()
    logger.info(f"[db_container] Postgres ready at {info.get('host')}:{info.get('port')}")
    return info


def get_connection_info() -> Dict[str, str]:
    if _postgres_container is None:
        return {}
    return {
        "host": _postgres_container.get_container_host_ip(),
        "port": str(_postgres_container.get_exposed_port(5432)),
        "user": _postgres_container.username,
        "password": _postgres_container.password,
        "database": _postgres_container.dbname,
    }


def get_database_url() -> str:
    if _postgres_container is None:
        return ""
    info = get_connection_info()
    return f"postgresql://{info['user']}:{info['password']}@{info['host']}:{info['port']}/{info['database']}"


def update_env_file(workspace_path: str) -> bool:
    if _postgres_container is None:
        return False
    
    env_path = os.path.join(workspace_path, ".env")
    database_url = get_database_url()
    
    env_content = ""
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            env_content = f.read()
    
    if "DATABASE_URL=" in env_content:
        env_content = re.sub(r'DATABASE_URL=.*', f'DATABASE_URL="{database_url}"', env_content)
    else:
        env_content += f'\nDATABASE_URL="{database_url}"\n'
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)
    return True

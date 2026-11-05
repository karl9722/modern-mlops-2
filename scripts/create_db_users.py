import subprocess
from pathlib import Path

from dotenv import dotenv_values

config = dotenv_values(Path(".env"))

users = {
    "mlflow": ("MLFLOW_DB_PASSWORD", "mlflow"),
    "dagster": ("DAGSTER_DB_PASSWORD", "dagster"),
    "app": ("APP_DB_PASSWORD", "monitoring"),
}

for username, (password_key, database) in users.items():
    password = config.get(password_key)

    if not password:
        raise RuntimeError(f"Variable manquante : {password_key}")

    sql = f"""
SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L',
    '{username}',
    :'password'
)
WHERE NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = '{username}'
)
\\gexec

ALTER ROLE "{username}" PASSWORD :'password';
GRANT CONNECT ON DATABASE "{database}" TO "{username}";
"""

    command = [
        "docker", "compose", "exec", "-T",
        "postgres", "psql",
        "-U", "postgres",
        "-d", "postgres",
        "-v", "ON_ERROR_STOP=1",
    ]

    # Transmettre le secret par l'entrée standard,
    # sans le placer dans les arguments du processus.
    script = (
        "\\set password '" + password.replace("'", "''") + "'\n"
        + sql
    )

    result = subprocess.run(
        command,
        input=script,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Erreur pour {username} : {result.stderr}"
        )

    print(f"Utilisateur {username} : OK")

print("Configuration des utilisateurs terminée.")

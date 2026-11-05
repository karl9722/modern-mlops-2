"""Create local credentials once; never overwrite an existing .env or print secrets."""

import os
import secrets
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    template = (root / ".env.example").read_text()
    for name in (
        "postgres",
        "mlflow",
        "dagster",
        "app",
        "grafana-reader",
        "grafana-admin",
        "api-key",
    ):
        template = template.replace("change-me-" + name, secrets.token_urlsafe(24))
    try:
        fd = os.open(root / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print("Existing .env preserved.")
    else:
        with os.fdopen(fd, "w") as handle:
            handle.write(template)
        print("Created ignored .env with separate random credentials; values are not printed.")
    for name in ("data", "artifacts"):
        (root / name).mkdir(exist_ok=True)


if __name__ == "__main__":
    main()

from pathlib import Path
import re

path = Path("src/mlops/api.py")
code = path.read_text(encoding="utf-8-sig")

# Supprimer l'ancienne instrumentation
code = re.sub(
    r'\n?# Monitoring Prometheus\s*\nfrom prometheus_fastapi_instrumentator import Instrumentator\s*\n\s*Instrumentator\(\)\.instrument\(app\)\.expose\(app\)\s*',
    '\n',
    code,
)

# Ajouter l'import
if "from prometheus_fastapi_instrumentator import Instrumentator" not in code:
    code = "from prometheus_fastapi_instrumentator import Instrumentator\n" + code

# Ajouter l'instrumentation immédiatement après FastAPI(...)
pattern = r'(^app\s*=\s*FastAPI\([^\n]*\)\s*$)'
replacement = r'\1\n\nInstrumentator().instrument(app).expose(app)'

code, count = re.subn(pattern, replacement, code, count=1, flags=re.MULTILINE)

if count != 1:
    raise RuntimeError("Ligne app = FastAPI(...) introuvable. Aucune modification enregistrée.")

path.write_text(code, encoding="utf-8")
print("Instrumentation Prometheus corrigée.")

"""Ejecuta el notebook con el Python actual y conserva evidencia si falla una celda."""

import sys
from pathlib import Path

import nbformat
from jupyter_client import AsyncKernelManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    ruta = ROOT / "laboratorio-03.ipynb"
    notebook = nbformat.read(ruta, as_version=4)
    km = AsyncKernelManager(kernel_name="python3")
    km.kernel_spec.argv[0] = sys.executable
    cliente = NotebookClient(
        notebook, km=km, timeout=360, resources={"metadata": {"path": str(ROOT)}},
    )
    try:
        cliente.execute()
    finally:
        nbformat.write(notebook, ruta)
    print("Notebook ejecutado y guardado: laboratorio-03.ipynb", flush=True)

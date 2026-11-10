"""
Exporta las salidas de los notebooks del Laboratorio 1 a un archivo de texto.

Uso (desde la carpeta lab01, con el notebook ya ejecutado y guardado):
    python exportar_outputs.py
    python exportar_outputs.py lab01_content_safety.ipynb   # otro notebook

Genera: outputs/outputs_<nombre_notebook>.txt
Solo usa la librería estándar de Python.
"""
import json
import sys
from pathlib import Path

MAX_CHARS_POR_SALIDA = 4000  # recorta salidas muy largas (p. ej. el markdown completo)


def texto_de_salida(salida: dict) -> str:
    tipo = salida.get("output_type")
    if tipo == "stream":
        return "".join(salida.get("text", ""))
    if tipo in ("execute_result", "display_data"):
        datos = salida.get("data", {})
        return "".join(datos.get("text/plain", ""))
    if tipo == "error":
        return f"ERROR {salida.get('ename')}: {salida.get('evalue')}"
    return ""


def exportar(ruta_nb: Path) -> Path:
    nb = json.loads(ruta_nb.read_text(encoding="utf-8"))
    lineas = [f"NOTEBOOK: {ruta_nb.name}", "=" * 80]
    titulo_actual = ""
    celdas_codigo = sin_salida = 0

    for i, celda in enumerate(nb.get("cells", [])):
        fuente = "".join(celda.get("source", ""))
        if celda.get("cell_type") == "markdown":
            primera = fuente.strip().splitlines()[0] if fuente.strip() else ""
            if primera.startswith("#"):
                titulo_actual = primera.lstrip("# ").strip()
            continue

        celdas_codigo += 1
        salidas = celda.get("outputs", [])
        texto = "\n".join(t for t in (texto_de_salida(s) for s in salidas) if t).strip()
        lineas.append(f"\n--- Celda {i} | Sección: {titulo_actual} | ejecución [{celda.get('execution_count')}] ---")
        if not texto:
            sin_salida += 1
            lineas.append("(sin salida)")
            continue
        if len(texto) > MAX_CHARS_POR_SALIDA:
            texto = texto[:MAX_CHARS_POR_SALIDA] + f"\n... [recortado: {len(texto)} caracteres en total]"
        lineas.append(texto)

    lineas += ["", "=" * 80, f"Celdas de código: {celdas_codigo} | sin salida: {sin_salida}"]
    destino = ruta_nb.parent / "outputs" / f"outputs_{ruta_nb.stem}.txt"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text("\n".join(lineas), encoding="utf-8")
    return destino


if __name__ == "__main__":
    nombre = sys.argv[1] if len(sys.argv) > 1 else "lab01_document_intelligence.ipynb"
    ruta = Path(__file__).resolve().parent / nombre
    if not ruta.exists():
        sys.exit(f"No se encontró {ruta}. Ejecuta el script desde la carpeta lab01.")
    archivo = exportar(ruta)
    print(f"Listo: {archivo}")

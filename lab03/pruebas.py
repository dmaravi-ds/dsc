"""Pruebas observables del RAG y regresión de memoria, compactación y alcance."""

import re
import unicodedata
from datetime import datetime, timezone
from importlib.metadata import version

from lab03.agent import estado_memoria, preguntar_con_rag
from lab03.rag import guardar_json

CASOS = [
    {"id": "RAG-01", "tipo": "Pregunta directa",
     "pregunta": "¿Cuál es el ingreso mínimo mensual de la tarjeta Platinum?",
     "filtro": None, "chunk_esperado": "bca-tc-03", "datos": ["6000"],
     "esperado": "S/ 6,000 mensuales, con cita de la tabla de variantes."},
    {"id": "RAG-02", "tipo": "Pregunta reformulada",
     "pregunta": "¿Cuánto debe ganar al mes alguien para acceder al plástico Platinum?",
     "filtro": None, "chunk_esperado": "bca-tc-03", "datos": ["6000"],
     "esperado": "El mismo ingreso mínimo, aunque cambien las palabras."},
    {"id": "RAG-03", "tipo": "Información en otro chunk",
     "pregunta": "¿En qué horario atienden las agencias de lunes a viernes?",
     "filtro": None, "chunk_esperado": "bca-inst-03", "datos": ["9:00", "18:00"],
     "esperado": "Lunes a viernes de 9:00 a 18:00, citando canales de atención."},
    {"id": "RAG-04", "tipo": "Pregunta con filtro",
     "pregunta": "¿Qué requisitos se deben cumplir para solicitar Crédito Efectivo?",
     "filtro": "Crédito Efectivo", "chunk_esperado": "bca-ce-06", "datos": ["dni"],
     "esperado": "Requisitos de Crédito Efectivo; todos los chunks de esa categoría."},
    {"id": "RAG-05", "tipo": "Información ausente",
     "pregunta": "¿Cuál es el monto exacto en dólares de la cobertura del seguro de viaje de Platinum?",
     "filtro": "Tarjeta de Crédito", "chunk_esperado": None, "datos": [],
     "esperado": "Reconocer que la cobertura exacta no está documentada, sin inventar una cifra."},
]


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def evaluar(caso, obtenido):
    """Reglas explícitas de comprobación, no una evaluación semántica infalible.

    Se deja siempre la respuesta íntegra y el texto recuperado para revisión humana.
    No se presenta una distancia baja como prueba de corrección.
    """
    texto = normalizar(obtenido["respuesta"])
    sin_separadores = re.sub(r"(?<=\d)[,.](?=\d{3}(?:\D|$))", "", texto)
    checks = {"alcance": obtenido["respuesta"].startswith("ALCANCE: EN_ALCANCE")}
    if caso["chunk_esperado"]:
        id_ = caso["chunk_esperado"]
        encontrados = obtenido["fragmentos"]
        fuente = next((f["metadata"]["fuente"] for f in encontrados if f["id"] == id_), "")
        checks.update({
            "chunk_correcto_recuperado": any(f["id"] == id_ for f in encontrados),
            "cita_id": id_ in obtenido["respuesta"],
            "cita_pdf": bool(fuente) and fuente in obtenido["respuesta"],
            "dato_esperado": all(d in sin_separadores for d in caso["datos"]),
        })
    else:
        checks["reconoce_ausencia"] = any(x in texto for x in [
            "no dispongo", "no disponemos", "no se especifica", "no especifica",
            "no indica", "no detalla", "no esta", "no aparece", "no se detalla",
            "informacion suficiente", "no se encuentra", "no cuento", "no contamos",
        ])
        # Un monto junto a USD/US$/dólares requeriría revisión; se penaliza.
        checks["sin_cobertura_inventada"] = not re.search(
            r"(?:usd|us\$)\s*[\d]+|[\d][\d,.]*\s*dolares", texto
        )
    if caso["filtro"]:
        checks["filtro_respetado"] = all(
            f["metadata"]["categoria"] == caso["filtro"] for f in obtenido["fragmentos"]
        )
    fallos = [k for k, v in checks.items() if not v]
    return {
        "evaluacion": "correcto" if not fallos else ("parcial" if any(checks.values()) else "incorrecto"),
        "justificacion": "Cumple todas las comprobaciones explícitas del caso." if not fallos
                         else "Revisar: " + ", ".join(fallos),
        "comprobaciones": checks,
        "metodo_evaluacion": "Reglas explícitas; respuesta y fuentes disponibles para revisión humana.",
    }


async def ejecutar_pruebas(agente, rag, sesion=None):
    """Una sesión compartida para demostrar que RAG no elimina memoria/compacción."""
    sesion = sesion if sesion is not None else agente.create_session()
    resultados, conversacion = [], []
    perfil = (
        "Perfil completamente ficticio: el cliente Luis M. tiene ingreso neto de S/ 7,200, "
        "es dependiente y tiene una oferta PRE-APROBADA de Crédito Efectivo de S/ 35,000, "
        "a TEA 18.9%, vigente por diez días. Quiere remodelar su casa. "
        "Confirma que recordarás estos datos; no recomiendes productos todavía."
    )
    respuesta = await agente.run(perfil, session=sesion)
    conversacion.append({"tipo": "registro_perfil", "pregunta": perfil,
                         "respuesta": respuesta.text, "memoria": estado_memoria(sesion)})
    guardar_json("conversacion.json", conversacion)
    for caso in CASOS:
        obtenido = await preguntar_con_rag(
            agente, sesion, rag, caso["pregunta"], categoria=caso["filtro"]
        )
        fila = {**caso, **obtenido, **evaluar(caso, obtenido)}
        resultados.append(fila)
        conversacion.append(fila)
        guardar_json("pruebas_rag.json", resultados)
        guardar_json("conversacion.json", conversacion)
        print(f"{caso['id']} | {fila['evaluacion']} | "
              f"chunks: {[f['id'] for f in obtenido['fragmentos']]} | memoria: {obtenido['memoria']}",
              flush=True)

    pregunta_memoria = (
        "Recuerda únicamente el perfil ficticio que te compartí al inicio: "
        "¿cuál es su ingreso neto, monto, tipo de oferta, TEA y vigencia? "
        "No consultes ni confundas condiciones generales con ese perfil."
    )
    respuesta = await agente.run(pregunta_memoria, session=sesion)
    texto = normalizar(respuesta.text).replace(",", "").replace(".", "")
    memoria = estado_memoria(sesion)
    checks_memoria = {
        "ingreso": "7200" in texto, "monto": "35000" in texto,
        "tipo_preaprobada": "pre-aprobada" in texto or "preaprobada" in texto or "pre aprobada" in texto,
        "tea": "189" in texto, "vigencia": "10" in texto or "diez" in texto,
        "compactacion_real": memoria["resumenes"] > 0 and memoria["excluidos"] > 0,
    }
    conversacion.append({"tipo": "memoria_tras_compactacion", "pregunta": pregunta_memoria,
                         "respuesta": respuesta.text, "memoria": memoria,
                         "comprobaciones": checks_memoria})
    for tipo, pregunta, esperado in [
        ("fuera_de_alcance", "¿Quién ganó el clásico de fútbol ayer?", "ALCANCE: FUERA_DE_ALCANCE"),
        ("otra_especialidad", "Quiero un crédito hipotecario para comprar un departamento.",
         "ALCANCE: OTRA_ESPECIALIDAD"),
    ]:
        respuesta = await agente.run(pregunta, session=sesion)
        conversacion.append({"tipo": tipo, "pregunta": pregunta, "respuesta": respuesta.text,
                             "correcto": respuesta.text.startswith(esperado),
                             "memoria": estado_memoria(sesion)})
    guardar_json("conversacion.json", conversacion)
    historial = sesion.state.get("historial", {}).get("messages", [])
    guardar_json("historial_compactado.json", [
        {"role": str(m.role), "text": m.text,
         "excluido": bool((m.additional_properties or {}).get("_excluded")),
         "es_resumen": "_summary_of_message_ids" in ((m.additional_properties or {}).get("_group") or {})}
        for m in historial
    ])
    resumen = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "estado": "ejecutado_en_azure",
        "llm": "gpt-5.6-luna", "embeddings": "text-embedding-3-small",
        "autenticacion": "DefaultAzureCredential / Microsoft Entra ID; sin API keys",
        "pruebas_rag": {c["id"]: c["evaluacion"] for c in resultados},
        "memoria_y_compactacion": checks_memoria,
        "alcance": {c["tipo"]: c["correcto"] for c in conversacion if "correcto" in c},
        "misma_sesion": True,
        "criterio_aprobacion": "Comprobaciones explícitas; no sustituye revisión humana de evidencia.",
        "versiones": {p: version(p) for p in ["agent-framework-core", "agent-framework-openai", "chromadb", "azure-identity"]},
    }
    resumen["comprobaciones_superadas"] = (
        all(c["evaluacion"] == "correcto" for c in resultados)
        and all(checks_memoria.values()) and all(resumen["alcance"].values())
    )
    guardar_json("resumen_ejecucion.json", resumen)
    return resultados, conversacion, resumen

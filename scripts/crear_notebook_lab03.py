"""Construye el notebook entregable del Lab 3 sin ejecutar servicios de Azure."""

from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell
nb.cells = [
    md("""# Laboratorio 3 · RAG del copiloto BancAnalytics
**Rama:** `l3_DSC_30ME`. Continuación de `laboratorio-02.ipynb`.

Caso: copiloto de asesores de un banco **100 % ficticio**. Conserva su rol,
restricciones de alcance, memoria de corto plazo y compactación por resúmenes.
Ahora responde condiciones de productos usando recuperación documental.
No se implementan Tools, MCP ni agentes como herramientas: solo se diseñan.

## 1. Validación del Laboratorio 2 y entorno
La configuración se lee del notebook anterior sin ejecutar sus celdas. Se conservan
rol, objetivos, restricciones, formato, `InMemoryHistoryProvider` y
`CompactionProvider` con `SummarizationStrategy`. La KB incrustada y el ejemplo con
la respuesta de Platinum se sustituyen por contexto recuperado. El original no cambia.

Seleccione **Python (dsc .env-dsc)**. Requiere `pip install -r requirements.txt`,
sesión de Azure CLI (`az login`) con permisos asignados y `.env` local basado en `env`.
Solo se envían textos sintéticos a los dos deployments de Azure. No hay API keys.
La ejecución completa genera nuevas llamadas de consumo a Azure; la colección local
se reutiliza cuando no cambia su huella. Los resultados guardados permiten revisarla
sin volver a ejecutar.
"""),
    code("""from pathlib import Path
import sys
ROOT = Path.cwd()
if not (ROOT / 'laboratorio-02.ipynb').exists():
    ROOT = ROOT.parent
if not (ROOT / 'laboratorio-02.ipynb').exists():
    raise RuntimeError('Abra este notebook dentro del repositorio dsc.')
sys.path.insert(0, str(ROOT))
from IPython.display import display, Markdown
from lab03.rag import preparar_chunks, RepositorioRAG, guardar_json, OUTPUT
from lab03.agent import crear_clientes, crear_agente, configuracion_lab2
from lab03.pruebas import ejecutar_pruebas

credential, cliente_llm, cliente_embeddings, endpoint, modelo_embedding = crear_clientes()
agente, procedencia = crear_agente(cliente_llm, target_count=4, threshold=2)
sesion = agente.create_session()
guardar_json('procedencia_lab2.json', procedencia)
print('Agente:', procedencia['agente'])
print('Origen:', procedencia['notebook_origen'], '| SHA-256:', procedencia['sha256_origen'])
print('Autenticación: Microsoft Entra ID / DefaultAzureCredential')
print('Modelos: gpt-5.6-luna /', modelo_embedding)
print('Compactación de demostración: conserva 4 mensajes recientes; margen 2.')
"""),
    md("""## 2. Conocimiento y estrategia de chunking
Reutilizamos el JSON extraído en el Lab 1: `outputs/bancanalytics_kb_index.json`.
Son tres PDF sintéticos: información institucional, tarjetas y Crédito Efectivo.
No mezclamos las condiciones de la guía Nova Andino de `lab01` con BancAnalytics.

**Estrategia:** división por estructura: una sección del índice = un chunk, con
título original como contexto. Límite de validación: **1,800 caracteres de contenido**
por sección; sin solapamiento. Ninguna sección actual supera el límite. Las tablas
se conservan completas para no separar ingresos, tasas y variantes. Si una sección
futura lo supera, el proceso pide revisar la segmentación en vez de truncarla.

**¿Por qué esta estrategia?** Las secciones ya son unidades temáticas. Un corte
fijo rompería filas de tablas; el solapamiento duplicaría condiciones y ocuparía
contexto innecesario. El título y la procedencia hacen interpretable cada fragmento.
"""),
    code("""chunks = preparar_chunks()
guardar_json('chunks.json', chunks)
documentos = sorted({c['metadata']['fuente'] for c in chunks})
categorias = sorted({c['metadata']['categoria'] for c in chunks})
print('Documentos:', len(documentos), documentos)
print('Categorías:', categorias)
print('Chunks:', len(chunks), '| IDs únicos:', len({c['id'] for c in chunks}))
print('Longitud máxima con título:', max(len(c['text']) for c in chunks))
display(chunks[0])
"""),
    md("""## 3. Estructura de chunks y metadatos
| Campo | Uso |
|---|---|
| `id` | ID único de sección del Lab 1; trazabilidad y actualización. |
| `text` → document | Título y contenido original recuperable. |
| embedding | Vector de Azure, fuera de los metadatos. |
| `categoria` | Filtro: Institucional, Tarjeta de Crédito o Crédito Efectivo. |
| `fuente`, `titulo`, `paginas` | Contexto y cita de origen. Páginas como texto simple. |
| `numero_chunk` | Orden dentro del documento. |
| `tipo_documento`, `sintetico` | Descripción/control de procedencia; futuros filtros posibles. |

**¿Qué elegimos para filtrar y qué para contexto?** En las pruebas filtramos
`categoria`; mostramos `fuente`, `titulo`, páginas e ID como contexto y procedencia.
Todos los metadatos son escalares; no se guardan listas ni objetos anidados.
Chroma no requiere declarar campos filtrables: los filtros se aplican a metadata.
"""),
    md("""## 4. Embeddings con Microsoft Agent Framework y Azure
Usamos `OpenAIEmbeddingClient`, `DefaultAzureCredential` y el deployment
`text-embedding-3-small` en el mismo endpoint del LLM. Documentos y preguntas usan
el mismo cliente/modelo. No hay Sentence Transformers ni embeddings automáticos de Chroma.
"""),
    code("""prueba_embedding = await cliente_embeddings.get_embeddings(
    ['Consulta ficticia de prueba para BancAnalytics.']
)
dimension = len(prueba_embedding[0].vector)
assert dimension > 0
print('Dimensiones del vector numérico generado en Azure:', dimension)
"""),
    md("""## 5. Persistencia y recuperación en ChromaDB
Base local en `chroma_proyecto/`, fuera de Git. Usamos `PersistentClient`, métrica
cosine, `embedding_function=None` y vectores explícitos de Azure. La huella de
contenido, estrategia, modelo y endpoint identifica la colección: una nueva versión
no se mezcla con registros obsoletos. `upsert` carga IDs únicos.

La distancia es **1 − similitud del coseno**: menor distancia significa mayor
similitud, pero no garantiza que el fragmento responda. No imponemos un umbral
arbitrario: el agente debe verificar que el contenido sustente el dato.
"""),
    code("""rag = RepositorioRAG(cliente_embeddings, modelo_embedding, endpoint)
manifiesto = await rag.indexar(chunks)
guardar_json('indice_manifest.json', manifiesto)
display(manifiesto)
assert manifiesto['chunks'] == len(chunks)
assert manifiesto['dimensiones'] == dimension
"""),
    code("""pregunta = '¿Qué requisitos tiene Crédito Efectivo?'
sin_filtro = await rag.recuperar(pregunta)
con_filtro = await rag.recuperar(pregunta, categoria='Crédito Efectivo')
guardar_json('comparacion_filtros.json', {'pregunta': pregunta, 'sin_filtro': sin_filtro, 'con_filtro': con_filtro})
for nombre, fragmentos in [('SIN FILTRO', sin_filtro), ('FILTRO: Crédito Efectivo', con_filtro)]:
    print(nombre)
    for f in fragmentos:
        print(f['id'], '|', f['metadata']['categoria'], '|', f['metadata']['fuente'], '| distancia:', round(f['distancia'], 4))
assert con_filtro and all(f['metadata']['categoria'] == 'Crédito Efectivo' for f in con_filtro)
"""),
    md("""## 6. Integración con el mismo agente
Flujo: **pregunta → embedding de Azure → ChromaDB → contexto con citas →
CopilotoAsesorBancAnalytics → respuesta**. La recuperación es una función del flujo,
no una Tool. `preguntar_con_rag` pasa la **misma sesión** a `agente.run`.
La KB ya no se inyecta completa en el prompt; solo los tres fragmentos recuperados.
El historial recuerda el perfil ficticio del asesor; las condiciones de productos
deben sustentarse en el contexto de la consulta actual. El prompt trata los documentos
como datos y exige reconocer información ausente.
"""),
    md("""## 7. Cinco pruebas de RAG y regresión del Lab 2
Se registra primero un perfil ficticio; después se ejecutan las cinco pruebas y
se vuelve a pedir el perfil tras la compactación. Se comprueba también el rechazo
de fútbol y la derivación de hipotecas. Todo ocurre en la **misma sesión**.

Evaluaciones: `correcto`, `parcial` o `incorrecto`, con comprobaciones y justificación.
Las reglas verifican datos esperados, cita, chunk y filtro; **no sustituyen una
revisión humana** del texto completo. Las distancias se guardan para inspección.
La compactación se acredita con mensajes excluidos y resúmenes reales del framework,
no únicamente con el número de turnos.
"""),
    code("""resultados, conversacion, resumen = await ejecutar_pruebas(agente, rag, sesion=sesion)
for caso in resultados:
    display(Markdown(f\"### {caso['id']} · {caso['tipo']} · {caso['evaluacion']}\\n\"
                     f\"**Pregunta:** {caso['pregunta']}\\n\\n\"
                     f\"**Filtro:** {caso['filtro']} · **Esperado:** {caso['esperado']}\\n\\n\"
                     f\"{caso['respuesta']}\\n\\n**Evaluación:** {caso['justificacion']}\"))
    display([{'id': f['id'], 'fuente': f['metadata']['fuente'], 'distancia': f['distancia']} for f in caso['fragmentos']])
display(resumen)
"""),
    code("""memoria = next(c for c in conversacion if c['tipo'] == 'memoria_tras_compactacion')
display(Markdown('### Perfil recordado tras compactación\\n' + memoria['respuesta']))
display(memoria['memoria'])
display(memoria['comprobaciones'])
"""),
    md("""### Reflexión: ¿dónde funcionó y qué dificultades observamos?
Las pruebas distinguen recuperación y respuesta: encontrar un chunk no demuestra
que el dato esté presente. La consulta de cobertura de seguro es deliberadamente
difícil: la tabla indica que existe seguro de viaje, pero no su suma asegurada.
El agente debe reconocer esa ausencia aunque recupere el documento correcto.

Una sección de exoneración de membresía contiene texto extraído defectuoso; no lo
corregimos inventando cifras y no lo usamos como evidencia de condiciones exactas.
La tabla completa preserva relaciones, pero limita la precisión por fila; en una
colección más grande convendría normalizar tablas y validar un conjunto mayor de
preguntas. Este laboratorio pequeño no estima una precisión general de producción.
El resultado observado de cada caso y sus posibles dificultades aparece abajo.
"""),
    code("""for caso in resultados:
    print(caso['id'], caso['evaluacion'], '—', caso['justificacion'])
print('Memoria y compactación:', resumen['memoria_y_compactacion'])
print('Alcance:', resumen['alcance'])
print('Comprobaciones superadas:', resumen['comprobaciones_superadas'])
print('Evidencia completa en:', OUTPUT.relative_to(ROOT))
"""),
    md("""## 8. Diseño de Tools y evaluación de Agent as a Tool
**Solo planificación; no implementadas en este laboratorio.**

| Nombre | Propósito/cuándo | Entradas | Salidas | Fuente prevista | Justificación |
|---|---|---|---|---|---|
| `buscar_conocimiento` | Consultar condiciones documentadas; elegir búsqueda cuando sea necesaria. | pregunta: str, categoría: str opcional, top_k: int 1–5 | chunks, distancia, ID, PDF/página | Chroma local con documentos sintéticos | Recuperación comprobable y filtros; el LLM no debe memorizar condiciones. |
| `consultar_oferta_demo` | Ver perfil/oferta ficticia vigente antes de orientar al asesor. | cliente_id: str con prefijo CLI-DEMO | encontrado: bool, perfil, tipo de oferta, monto, TEA, vigencia o error | JSON local 100 % sintético | No inventar ofertas ni convertir una pre-aprobada en aprobada; validar ID y caso ausente. |
| `simular_cuota_referencial` | Calcular cuota del sistema francés a pedido del asesor. | monto: número positivo, tea_pct: número no negativo, meses: entero positivo | cuota, total, interés, supuestos o error | Fórmula local con parámetros ficticios | Cálculo determinista, validación de plazo/tasa y tasa cero; excluye seguros y comisiones, no aprueba créditos. |

**¿Hace falta Agent as a Tool?** No por ahora: un único copiloto cubre tarjetas,
Crédito Efectivo y consultas institucionales. Recuperación y cálculo son funciones
acotadas; otro LLM añadiría latencia sin una responsabilidad necesaria distinta.
Las hipotecas se derivan verbalmente a otra especialidad, sin simular una llamada.
Si se amplía el alcance, un especialista hipotecario recibiría únicamente una
consulta/perfil ficticio mínimo y devolvería orientación documentada con citas y
límites, nunca una aprobación. Habría que evaluar utilidad antes de implementarlo.

## 9. Entregables y reproducción
- Notebook principal `laboratorio-03.ipynb` con salidas reales de Azure.
- Módulos `lab03/rag.py`, `lab03/agent.py`, `lab03/pruebas.py`.
- Evidencias JSON en `lab03/outputs/`: chunks, manifiesto, consultas con/sin filtro,
  cinco pruebas, conversación, historial compactado y resumen de ejecución.
- Pruebas locales: `python -m unittest lab03.test_rag -v` (fixture explícita; no Azure).
- Ejecución completa: `python scripts/ejecutar_lab03.py`.

La guía solicita un PR **no borrador** de `l3_DSC_30ME` hacia `main` en
`dmaravi-ds/dsc`, abierto desde la cuenta del participante.

Referencias técnicas: [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/),
[cliente OpenAI](https://github.com/microsoft/agent-framework/tree/main/python/packages/openai),
[colecciones Chroma](https://docs.trychroma.com/docs/collections/manage-collections).
"""),
    code("""credential.close()
assert resumen['comprobaciones_superadas'], 'Hay comprobaciones pendientes: revise pruebas_rag.json y conversacion.json.'
print('Laboratorio 3: ejecución completa y comprobaciones explícitas superadas.')
"""),
]
nb.metadata = {
    "kernelspec": {"display_name": "Python (dsc .env-dsc)", "language": "python", "name": "dsc"},
    "language_info": {"name": "python", "version": "3.12"},
}
nbf.write(nb, ROOT / "laboratorio-03.ipynb")
print("Creado laboratorio-03.ipynb (sin ejecutar).")

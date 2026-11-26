# dsc

## Entorno local en Windows

El entorno virtual de este equipo es `.env-dsc/`, creado con Python 3.12.
El archivo `.env` contiene las variables de Azure y se inicializa desde el
archivo `env` del repositorio. `.env` queda excluido de Git; `env` es la
plantilla versionada de configuración y no debe contener secretos.

Desde la carpeta `dsc`, activa el entorno e instala las dependencias:

```powershell
.\.env-dsc\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

En otra copia del repositorio, primero crea el entorno con
`python -m venv .env-dsc` y copia `env` a `.env` si aún no existe ese archivo.
En VS Code selecciona `.env-dsc\Scripts\python.exe` como intérprete de Python
y como kernel de los notebooks. Si abres `dsc` como carpeta de trabajo,
`.vscode/settings.json` propone ese intérprete por defecto.

Repositorio base de los laboratorios del programa de **Data Science** (Credicorp × NTT DATA).
Cada equipo trabaja en su propio fork y entrega cada laboratorio con un pull request.

## Cómo empezar (una vez por equipo)

1. El capitán del equipo hace **fork** de este repositorio en su cuenta personal de GitHub, sin cambiarle el nombre.
   El portal detecta solo el fork `<capitan>/dsc`; no hay que registrar nada.
2. El capitán agrega a sus compañeros como colaboradores del fork.
3. Cada integrante clona el fork y trabaja ahí.

```bash
git clone https://github.com/<capitan>/dsc.git
cd dsc
```

## Cómo entregar un laboratorio

Cada laboratorio se entrega con un pull request del equipo. Basta con uno; si varios integrantes abren el suyo,
cuentan todos los válidos. Cada PR sale de una rama con este nombre:

```
l<N>_DSC_<CÓDIGO>
```

- `<N>`: el número del laboratorio (`l1`, `l2`, …).
- `<CÓDIGO>`: el código de participante de quien abre el PR (por ejemplo `01AA`).

Ejemplo para el Laboratorio 1:

```bash
git switch -c l1_DSC_01AA
# … trabajo del laboratorio …
git add -A
git commit -m "feat: laboratorio 1"
git push -u origin l1_DSC_01AA
```

En GitHub, abre el PR **dentro del fork del equipo**, con base `main` y compare `l1_DSC_01AA`, listo para revisión
(no en borrador). El portal lo detecta solo y lo valida contra la guía del laboratorio.

## Estructura

Cada laboratorio indica en su guía qué carpetas y archivos crear. Mantén el código y las notas del equipo en este
repositorio; los datos, credenciales y archivos `.env` no se suben.

## Laboratorio 3: RAG de BancAnalytics

Abre `laboratorio-03.ipynb` con el entorno `.env-dsc`. Es una continuación del
copiloto de `laboratorio-02.ipynb`: conserva rol, restricciones, sesión y compactación,
y sustituye la base completa del prompt por recuperación local en ChromaDB.
Reutiliza tres documentos sintéticos del Lab 1; no mezcla las condiciones de
BancAnalytics con la guía Nova Andino de `lab01/`.

En `.env` deben existir estas variables de configuración (sin API keys):

```dotenv
FOUNDRY_MODEL_ENDPOINT=https://TU-RECURSO.services.ai.azure.com/openai/v1
FOUNDRY_MODEL_DEPLOYMENT=gpt-5.6-luna
FOUNDRY_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

Autentícate con `az login` usando la identidad asignada y permisos para los dos
deployments. El código usa `DefaultAzureCredential`; no guarda tokens en archivos.
Para registrar el kernel en una nueva instalación:

```powershell
python -m ipykernel install --prefix .env-dsc --name dsc --display-name "Python (dsc .env-dsc)"
```

Validación local sin Azure:

```powershell
python -m pip check
python -m unittest lab03.test_rag -v
```

Ejecutar todo el notebook con el intérprete activo (realiza llamadas a Azure):

```powershell
python scripts/ejecutar_lab03.py
```

La colección local `chroma_proyecto/` está excluida de Git y se reconstruye con
embeddings de Azure. La huella de configuración/contenido evita mezclar versiones;
las colecciones antiguas quedan aisladas. Las evidencias sintéticas y las cinco
pruebas con evaluación están en `lab03/outputs/`. El notebook ejecutado conserva
las respuestas y los resultados de memoria/compactación para revisar sin consumo
adicional. Las comprobaciones automáticas son específicas de los casos: no estiman
la calidad general de producción ni sustituyen la revisión de las respuestas.

`lab03/agent.py` lee solo la configuración del notebook anterior mediante AST; no
ejecuta sus celdas. `lab03/rag.py` prepara e indexa secciones; `lab03/pruebas.py`
registra respuestas, fuentes y evaluaciones. Las futuras Tools y Agent as a Tool
solo se diseñan en el notebook, conforme a la guía del Lab 3.

`scripts/crear_notebook_lab03.py` regenera la estructura del notebook **sin salidas**;
úsalo solo para cambiar su estructura y luego vuelve a ejecutarlo.

"""Preparación por secciones, embeddings de Azure y recuperación local en Chroma."""

import hashlib
import json
from pathlib import Path

import chromadb
from chromadb.config import Settings

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "lab03" / "outputs"
MAX_SECTION_CHARS = 1800
CHUNK_VERSION = "secciones-v1-max1800-sin-solapamiento"


def guardar_json(nombre, datos):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / nombre).write_text(
        json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def preparar_chunks(registros=None):
    """Reutiliza las secciones del Lab 1; nunca corta tablas ni inventa contexto.

    En esta colección todas las secciones caben en 1800 caracteres. Una futura
    sección más grande requiere revisar la estrategia, en vez de truncar texto.
    """
    if registros is None:
        registros = json.loads(
            (ROOT / "outputs/bancanalytics_kb_index.json").read_text(encoding="utf-8")
        )
    chunks, ids = [], set()
    por_documento = {}
    for registro in registros:
        if registro["id"] in ids:
            raise ValueError(f"ID duplicado: {registro['id']}")
        ids.add(registro["id"])
        contenido = registro["contenido"].strip()
        if not contenido or len(contenido) > MAX_SECTION_CHARS:
            raise ValueError(f"Revisar sección vacía o demasiado larga: {registro['id']}")
        if not registro.get("vigente") or "sintético" not in registro.get("origen", ""):
            raise ValueError("Esta colección admite únicamente fuentes sintéticas vigentes.")
        fuente = registro["fuente"]
        por_documento[fuente] = por_documento.get(fuente, 0) + 1
        chunks.append({
            "id": registro["id"],
            "text": f"{registro['titulo']}\n\n{contenido}",
            "metadata": {
                "fuente": fuente,
                "titulo": registro["titulo"],
                "categoria": registro["categoria"],
                "tipo_documento": registro["tipo_documento"],
                "numero_chunk": por_documento[fuente],
                "paginas": ",".join(map(str, registro["paginas"])),
                "sintetico": True,
            },
        })
    if not chunks:
        raise ValueError("No hay conocimiento para indexar.")
    return chunks


class RepositorioRAG:
    def __init__(self, embeddings, modelo, endpoint, path=None):
        self.embeddings = embeddings
        self.modelo = modelo
        self.endpoint = endpoint
        self.chroma = chromadb.PersistentClient(
            path=str(path or ROOT / "chroma_proyecto"),
            settings=Settings(anonymized_telemetry=False),
        )
        self.coleccion = None
        self.manifiesto = None

    async def indexar(self, chunks):
        # La huella evita mezclar modelos, recursos o versiones del conocimiento.
        # Una colección previa con otra huella queda aislada, nunca se consulta.
        entrada = {"chunks": chunks, "modelo": self.modelo,
                   "endpoint": self.endpoint, "estrategia": CHUNK_VERSION}
        huella = hashlib.sha256(
            json.dumps(entrada, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        nombre = f"bancanalytics_{huella[:20]}"
        self.coleccion = self.chroma.get_or_create_collection(
            name=nombre, embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
            metadata={"huella": huella, "modelo": self.modelo},
        )
        existentes = set(self.coleccion.get()["ids"])
        esperados = {c["id"] for c in chunks}
        if existentes != esperados:
            resultado = await self.embeddings.get_embeddings([c["text"] for c in chunks])
            vectores = [list(item.vector) for item in resultado]
            if len(vectores) != len(chunks) or not vectores or not vectores[0]:
                raise ValueError("Azure no devolvió un vector por chunk.")
            self.coleccion.upsert(
                ids=[c["id"] for c in chunks], documents=[c["text"] for c in chunks],
                metadatas=[c["metadata"] for c in chunks], embeddings=vectores,
            )
            obsoletos = list(existentes - esperados)
            if obsoletos:
                self.coleccion.delete(ids=obsoletos)
        muestra = self.coleccion.get(limit=1, include=["embeddings"])
        self.manifiesto = {
            "coleccion": nombre, "huella": huella, "modelo_embeddings": self.modelo,
            "dimensiones": len(muestra["embeddings"][0]), "chunks": self.coleccion.count(),
            "documentos": sorted({c["metadata"]["fuente"] for c in chunks}),
            "categorias": sorted({c["metadata"]["categoria"] for c in chunks}),
            "estrategia": CHUNK_VERSION, "metrica": "cosine",
        }
        return self.manifiesto

    async def recuperar(self, pregunta, categoria=None, top_k=3):
        if not isinstance(pregunta, str) or not pregunta.strip():
            raise ValueError("La pregunta debe ser texto no vacío.")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k debe ser un entero positivo.")
        if self.coleccion is None:
            raise RuntimeError("Primero hay que indexar el conocimiento.")
        if not self.coleccion.count():
            return []
        if categoria is not None:
            if not self.coleccion.get(where={"categoria": categoria}, limit=1)["ids"]:
                return []
        resultado = await self.embeddings.get_embeddings([pregunta])
        parametros = dict(
            query_embeddings=[list(resultado[0].vector)],
            n_results=min(top_k, self.coleccion.count()),
            include=["documents", "metadatas", "distances"],
        )
        if categoria is not None:
            parametros["where"] = {"categoria": categoria}
        encontrados = self.coleccion.query(**parametros)
        return [
            {"id": id_, "text": texto, "metadata": meta, "distancia": distancia}
            for id_, texto, meta, distancia in zip(
                encontrados["ids"][0], encontrados["documents"][0],
                encontrados["metadatas"][0], encontrados["distances"][0], strict=True
            )
        ]

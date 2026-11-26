"""Pruebas locales de integridad; embeddings falsos SOLO como fixture de pruebas."""

import tempfile
import unittest
from types import SimpleNamespace

from lab03.agent import configuracion_lab2
from lab03.rag import RepositorioRAG, preparar_chunks


class EmbeddingsDePrueba:
    """Fixture determinista de dos dimensiones; NO es evidencia de Azure."""
    def __init__(self):
        self.llamadas = 0

    async def get_embeddings(self, textos):
        self.llamadas += 1
        return [SimpleNamespace(vector=[1.0, 0.1] if "tarjeta" in t.lower() else [0.1, 1.0]) for t in textos]


class PruebasIntegridad(unittest.IsolatedAsyncioTestCase):
    def test_chunks_y_prompt_original(self):
        chunks = preparar_chunks()
        self.assertEqual(len(chunks), len({c["id"] for c in chunks}))
        self.assertGreaterEqual(len({c["metadata"]["fuente"] for c in chunks}), 2)
        self.assertGreaterEqual(len({c["metadata"]["categoria"] for c in chunks}), 2)
        self.assertTrue(all(isinstance(v, (str, bool, int, float)) for c in chunks for v in c["metadata"].values()))
        tabla = next(c["text"] for c in chunks if c["id"] == "bca-tc-03")
        self.assertIn("<table>", tabla)
        self.assertIn("</table>", tabla)
        prompt, resumen, _ = configuracion_lab2()
        self.assertIn("pre-aprobada", prompt)
        self.assertIn("No incluyas datos sensibles", resumen)
        self.assertNotIn("S/ 6,000 mensuales...", prompt)
        with self.assertRaises(ValueError):
            preparar_chunks([])

    async def test_filtros_persistencia_y_versiones(self):
        chunks = preparar_chunks()
        embeddings = EmbeddingsDePrueba()
        with tempfile.TemporaryDirectory() as temporal:
            rag = RepositorioRAG(embeddings, "fixture-local", "local://pruebas", path=temporal)
            manifiesto = await rag.indexar(chunks)
            await rag.indexar(chunks)
            self.assertEqual(embeddings.llamadas, 1)  # No recalcula una colección intacta.
            encontrados = await rag.recuperar("tarjeta", "Tarjeta de Crédito")
            self.assertTrue(encontrados)
            self.assertTrue(all(x["metadata"]["categoria"] == "Tarjeta de Crédito" for x in encontrados))
            self.assertEqual(await rag.recuperar("pregunta", "categoria_inexistente"), [])
            with self.assertRaises(ValueError):
                await rag.recuperar("", top_k=3)
            with self.assertRaises(ValueError):
                await rag.recuperar("pregunta", top_k=0)
            nuevo = await rag.indexar(chunks[:-1])
            self.assertNotEqual(nuevo["coleccion"], manifiesto["coleccion"])
            self.assertEqual(rag.coleccion.count(), len(chunks) - 1)
            # Cierra conexiones SQLite antes de borrar el directorio en Windows.
            from chromadb.api.shared_system_client import SharedSystemClient
            for sistema in list(SharedSystemClient._identifier_to_system.values()):
                sistema.stop()
            SharedSystemClient.clear_system_cache()


if __name__ == "__main__":
    unittest.main()

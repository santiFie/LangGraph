# Searcher Agent

## Descripción General

El `searcher_agent` (también llamado `researcher_agent`) es un agente especializado en recuperación de información. Combina búsqueda en internet con recuperación de documentos locales mediante RAG (Retrieval-Augmented Generation) sobre una colección de PDFs de Deep Learning y Minería de Datos.

---

## Capacidades

- **Búsqueda web en tiempo real** usando Tavily para consultas sobre temas generales, noticias recientes o documentación online.
- **Recuperación de documentos PDF locales** mediante RAG: busca en una colección de PDFs de Machine Learning/Deep Learning (textos de Ian Goodfellow, François Chollet, Michael Nielsen, y material de cursos universitarios sobre redes neuronales, CNN, autoencoders, GANs, etc.).
- **Síntesis de información**: Combina resultados de múltiples fuentes para generar respuestas completas y con citas.

---

## Restricciones y Notas

- Este agente es **completamente independiente** del resto (DSpace, MinIO, GitHub, Bots). No comparte archivos ni recursos con ellos.
- No puede ejecutar código, modificar archivos ni interactuar con APIs externas más allá de la búsqueda web.
- Es el agente más adecuado para preguntas del tipo "¿qué es...?", "¿cómo funciona...?", "busca información sobre...".
- La colección de PDFs está orientada a **Deep Learning y Minería de Datos**; para otros dominios técnicos, usa la búsqueda web.
- Si la pregunta requiere información actual o en tiempo real, prioriza Tavily sobre el RAG local.

# name
openalex_agent

# description
Agent for querying the OpenAlex academic database. Retrieves information about scientific works (articles, books, pre-prints, datasets), authors (ORCID profiles, h-index, metrics), institutions (universities, ROR IDs, academic output), topics (Wikidata-based fields of study), and sources (journals with ISSN-L). Always resolves human-readable names (e.g., "UNLP", "MIT") to canonical OpenAlex IDs before executing any filter query.

This is a read-only agent. Results are listed in a strict format: **Title**, Authors (max 3 + "et al."), Year/Source, Citations, DOI. It never synthesizes or explains article content, and never fabricates data. Independent of all other agents.

# inputs
- task: string — Academic query (e.g., "Find top-cited open access articles from Argentina in 2023", "Get works by author ORCID X", "List papers from institution ROR Y", "Find most cited works on topic Z").

# outputs
- result: string — Structured list in format: **Title**, Authors, Year and Source. Citations: X. DOI: Y. Returns explicit "no results found" message if the query yields no matches.
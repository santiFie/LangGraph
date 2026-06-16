# name
searcher_agent

# description
Agent specialized in information retrieval combining real-time web search and local RAG over a PDF collection focused on Deep Learning and Data Mining (Ian Goodfellow, François Chollet, Michael Nielsen, university course materials on neural networks, CNNs, autoencoders, GANs). Uses Tavily for live web queries and a FAISS-based retriever for the local PDF collection. Includes a self-critique loop with an academic reviewer to validate response quality before returning.

Best suited for conceptual questions ("what is X?", "how does Y work?") or research queries. For real-time or current information, it prioritizes web search over local RAG. Completely independent of DSpace, MinIO, GitHub, Bots, and OpenAlex.

# inputs
- task: string — Information retrieval query (e.g., "Explain how transformers work", "Search for recent news about LLMs", "What is backpropagation?", "Find information about GANs"). Can be in any language.

# outputs
- result: string — Synthesized, citation-backed response combining results from web search and/or local RAG. Responds in the same language as the input query.

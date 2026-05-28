from langchain_core.tools import tool

_VECTORSTORE_RETRIEVER = None

@tool("deep-learning-rag-retriever")
async def deep_learning_rag_retriever(query: str) -> str:
    """Search and return information about basic deep learning topics."""
    global _VECTORSTORE_RETRIEVER
    
    # Lazy initialization
    if _VECTORSTORE_RETRIEVER is None:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_community.document_loaders import PyMuPDFLoader
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_chroma import Chroma
        from glob import glob

        pdf_paths = glob("./rag_pdfs/*.pdf")
        if not pdf_paths:
            raise FileNotFoundError("No PDF files found in ./rag_pdfs/*.pdf")

        all_docs = []
        for path in pdf_paths:
            loader = PyMuPDFLoader(path)
            all_docs.extend(loader.load())

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
        doc_splits = text_splitter.split_documents(all_docs)

        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

        vectorstore = Chroma.from_documents(
            documents=doc_splits,
            embedding=embeddings,
            collection_name="deep-learning-rag"
        )
        _VECTORSTORE_RETRIEVER = vectorstore.as_retriever(search_kwargs={"k": 5})

    docs = await _VECTORSTORE_RETRIEVER.ainvoke(query)
    return "\n\n".join([doc.page_content for doc in docs])

def generate_retriever():
    return deep_learning_rag_retriever
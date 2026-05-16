from langchain_core.tools.retriever import create_retriever_tool
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyMuPDFLoader
from glob import glob

def generate_retriever():
    # Expand glob pattern to actual file paths and load each PDF separately
    pdf_paths = glob("./rag_pdfs/*.pdf")
    if not pdf_paths:
        raise FileNotFoundError("No PDF files found in ./rag_pdfs/*.pdf")

    all_docs = []
    for path in pdf_paths:
        loader = PyMuPDFLoader(path)
        all_docs.extend(loader.load())

    # Target documents 
    target_docs = [doc for doc in all_docs]

    # Splitter - Increase chunk_size
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    doc_splits = text_splitter.split_documents(target_docs)

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        embedding=embeddings,
        collection_name="deep-learning-rag"
    )

    # Fetch more context chunks
    retriever_pdf = vectorstore.as_retriever(search_kwargs={"k": 5})

    retriever_tool = create_retriever_tool(
        retriever_pdf,
        "deep-learning-rag-retriever",
        "Search and return information about basic deep learning topics.",
    )

    return retriever_tool
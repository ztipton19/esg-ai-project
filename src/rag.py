# RAG system for standards
"""RAG system for querying ESG standards"""
import os
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

load_dotenv()

class ESGStandardsRAG:
    def __init__(self, standards_dir="data/esg_standards"):
        self.standards_dir = standards_dir
        self.vectorstore = None
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
    def load_documents(self):
        """Load all PDFs from standards directory"""
        documents = []
        
        for filename in os.listdir(self.standards_dir):
            if filename.endswith('.pdf'):
                filepath = os.path.join(self.standards_dir, filename)
                loader = PyPDFLoader(filepath)
                docs = loader.load()
                documents.extend(docs)
        
        print(f"Loaded {len(documents)} pages from standards")
        return documents
    
    def create_vectorstore(self):
        """
        Creates a vector database if one doesn't exist; 
        otherwise, loads the existing one from disk.
        """
        persist_directory = "data/chroma_db"
        
        # 1. Setup Embeddings (Always needed to either read or write to the DB)
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )

        # 2. Check if the database folder already exists
        if os.path.exists(persist_directory) and os.listdir(persist_directory):
            print(f"--- Found existing database at {persist_directory}. Loading... ---")
            self.vectorstore = Chroma(
                persist_directory=persist_directory, 
                embedding_function=embeddings
            )
        else:
            print(f"--- No database found. Creating new one at {persist_directory}... ---")
            
            # Load and split documents only if we actually need to create the DB
            documents = self.load_documents()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            splits = text_splitter.split_documents(documents)
            
            self.vectorstore = Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                persist_directory=persist_directory
            )
            print(f"--- Database created with {len(splits)} chunks. ---")
        
    def query(self, question):
        """Query the ESG standards and get answer"""
        if not self.vectorstore:
            self.create_vectorstore()
        
        # Find relevant documents
        relevant_docs = self.vectorstore.similarity_search(question, k=3)
        
        # Build context from relevant docs
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        # Create prompt
        prompt = f"""Based on the following ESG standards documentation, answer this question:

Question: {question}

Relevant Standards:
{context}

Provide a clear, concise answer citing specific standards when possible."""

        # Get response from Claude
        response = self.llm.predict(prompt)
        
        return {
            "answer": response,
            "sources": [doc.metadata.get('source', 'Unknown') for doc in relevant_docs]
        }

# Test it
if __name__ == "__main__":
    rag = ESGStandardsRAG()
    
    test_questions = [
        "What is Scope 2 according to GRI standards?",
        "How should companies report electricity emissions?"
    ]
    
    for q in test_questions:
        print(f"\nQ: {q}")
        result = rag.query(q)
        print(f"A: {result['answer']}")
        print(f"Sources: {result['sources']}")
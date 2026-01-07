# RAG system for standards
"""RAG system for querying ESG standards"""
import os
import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

load_dotenv()

class ESGStandardsRAG:
    def __init__(self, standards_dir="data/esg_standards"):
        self.standards_dir = standards_dir
        self.vectorstore = None
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
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
        persist_directory = "data/chroma_db"
        
        # 1. Setup Embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )

        # 2. FORCE disk connection with a PersistentClient
        # This is the secret sauce for making sure the folder isn't empty
        client = chromadb.PersistentClient(path=persist_directory)

        # 3. Connect the LangChain wrapper to that specific client
        self.vectorstore = Chroma(
            client=client,
            collection_name="esg_standards", # Using a named collection is more stable
            embedding_function=embeddings,
        )

        # 4. Check if we actually have data inside the DB
        # We check the database itself rather than the folder
        existing_count = len(self.vectorstore.get()['ids'])

        if existing_count > 0:
            print(f"--- Found {existing_count} existing chunks in the database. ---")
        else:
            print(f"--- Database empty. Processing PDFs into {persist_directory}... ---")
            
            documents = self.load_documents()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            splits = text_splitter.split_documents(documents)
            
            # Add the documents directly to our client-backed store
            self.vectorstore.add_documents(documents=splits)
            
            # Explicit verification
            new_count = len(self.vectorstore.get()['ids'])
            print(f"--- Success! {new_count} chunks committed to disk. ---")
        
    def query(self, question):
            """Query the ESG standards and get answer"""
            if not self.vectorstore:
                self.create_vectorstore()
            
            relevant_docs = self.vectorstore.similarity_search(question, k=3)
            context = "\n\n".join([doc.page_content for doc in relevant_docs])
            
            prompt = f"""Based on the following ESG standards documentation, answer this question:

    Question: {question}

    Relevant Standards:
    {context}

    Provide a clear, concise answer citing specific standards when possible."""

            # USE .invoke() instead of .predict()
            # The result of .invoke() is an AIMessage object, so we grab .content
            try:
                response = self.llm.invoke(prompt)
                answer = response.content
            except Exception as e:
                print(f"Error calling Claude: {e}")
                answer = "Error: Could not retrieve answer from Claude."
            
            return {
                "answer": answer,
                "sources": list(set([doc.metadata.get('source', 'Unknown') for doc in relevant_docs]))
            }


# Test it
if __name__ == "__main__":
    print("--- Script Starting ---", flush=True)
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
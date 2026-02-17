from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from app.core.config import settings

def get_vector_store():
    """
    Returns the initialized Pinecone Vector Store.
    Uses OpenAI Embeddings (1536 dimensions) to translate text to numbers.
    """
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small", 
        api_key=settings.OPENAI_API_KEY
    )
    
    vector_store = PineconeVectorStore(
        index_name=settings.PINECONE_INDEX_NAME,
        embedding=embeddings,
        pinecone_api_key=settings.PINECONE_API_KEY
    )
    return vector_store
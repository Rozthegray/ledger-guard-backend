import uuid
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.documents import Document
from app.core.config import settings
from app.services.vector_store import get_vector_store
from fastapi.concurrency import run_in_threadpool # 🟢 1. IMPORT THIS

# Initialize Fast LLM
llm = ChatGroq(
    temperature=0, 
    model_name="llama-3.3-70b-versatile", # Active Model
    api_key=settings.GROQ_API_KEY
)

async def normalize_transaction(raw_description: str):
    # --- DEFENSIVE START: VECTOR DB ---
    vector_db = None
    similar = []
    
    try:
        vector_db = get_vector_store()
        # 🟢 2. FIX: Run blocking DB call in a thread
        # This prevents "Sync client is not available" error
        similar = await run_in_threadpool(vector_db.similarity_search_with_score, raw_description, k=1)
        
        if similar and similar[0][1] > 0.85:
            return {
                "category": similar[0][0].metadata['category'],
                "source": f"Memory Recall (Similarity: {similar[0][1]:.2f})",
                "confidence": similar[0][1]
            }    
    except Exception as e:
        # Just print error and move to AI (don't crash)
        print(f"⚠️ VECTOR DB SKIP: {str(e)}")
        
    # --- DEFENSIVE END ---

    # 2. ASK THE LLM
    print(f"🤖 AI Reasoning: Categorizing '{raw_description}'...")
    
    try:
        # Define Prompt
        prompt = ChatPromptTemplate.from_template(
            """
            You are an expert accountant. Categorize this bank transaction description into ONE 
            standard accounting category (e.g., Software, Office Supplies, Travel, Payroll, Utility).
            Return ONLY the category name. No periods. No extra words.
            
            Transaction: {text}
            """
        )
        chain = prompt | llm
        
        # 🟢 3. Run AI Inference (This is already async, so we await it directly)
        response = await chain.ainvoke({"text": raw_description})
        category = response.content.strip()

        # 3. Save to Memory (if successful)
        if vector_db:
            try:
                doc = Document(
                    page_content=raw_description,
                    metadata={"category": category, "source": "ai-learned"}
                )
                # 🟢 4. Run blocking Add call in thread too
                await run_in_threadpool(vector_db.add_documents, [doc])
            except:
                pass
        
        return {
            "category": category,
            "source": "Llama 3 Inference",
            "confidence": 0.7 
        }

    except Exception as e:
        print(f"❌ LLM ERROR: {str(e)}")
        
        # --- FALLBACK LOGIC ---
        desc_lower = raw_description.lower()
        fallback_cat = "Uncategorized"
        if "transfer" in desc_lower: fallback_cat = "Transfer"
        elif "net" in desc_lower or "data" in desc_lower: fallback_cat = "Utilities"
        elif "food" in desc_lower or "restaurant" in desc_lower: fallback_cat = "Meals"
        
        return {
            "category": fallback_cat, 
            "source": "Fallback Rule", 
            "confidence": 0.1
        }
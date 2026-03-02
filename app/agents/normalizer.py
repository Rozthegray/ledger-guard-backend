import uuid
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage # 🟢 1. IMPORT FOR MULTIMODAL (IMAGES)
from langchain_groq import ChatGroq
from langchain_core.documents import Document
from app.core.config import settings
from app.services.vector_store import get_vector_store
from fastapi.concurrency import run_in_threadpool 

# Initialize Fast Text LLM
llm = ChatGroq(
    temperature=0, 
    model_name="llama-3.3-70b-versatile", 
    api_key=settings.GROQ_API_KEY
)

# 🟢 2. INITIALIZE VISION LLM
vision_llm = ChatGroq(
    temperature=0,
    model_name="llama-3.2-90b-vision-preview", # Groq's Vision Model
    api_key=settings.GROQ_API_KEY
)

async def normalize_transaction(raw_description: str = None, image_base64: str = None, mime_type: str = "image/jpeg"):
    vector_db = None
    try:
        vector_db = get_vector_store()
    except Exception as e:
        print(f"⚠️ VECTOR DB INIT ERROR: {str(e)}")

    # ==========================================
    # 🟢 PATH A: IMAGE PROVIDED (RECEIPT/INVOICE)
    # ==========================================
    if image_base64:
        print("📸 Image detected. Using Vision AI to extract and categorize...")
        try:
            # We ask the vision model to do BOTH OCR and Categorization in one step
            message = HumanMessage(
                content=[
                    {
                        "type": "text", 
                        "text": "You are an expert accountant. Analyze this receipt or invoice. Extract a short description of the transaction, and assign ONE standard accounting category (e.g., Software, Office Supplies, Meals, Travel, Utilities). Return ONLY a valid JSON object with keys 'description' and 'category'. Do not use markdown blocks."
                    },
                    {
                        "type": "image_url", 
                        "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}
                    },
                ]
            )
            
            vision_response = await vision_llm.ainvoke([message])
            
            # Clean response if the LLM adds markdown by accident
            clean_json_str = vision_response.content.strip().replace("```json", "").replace("```", "")
            result = json.loads(clean_json_str)
            
            category = result.get("category", "Uncategorized")
            extracted_desc = result.get("description", "Image Upload Transaction")

            # Save the vision findings to the text Vector DB for future memory!
            if vector_db:
                try:
                    doc = Document(
                        page_content=extracted_desc,
                        metadata={"category": category, "source": "ai-vision-learned"}
                    )
                    await run_in_threadpool(vector_db.add_documents, [doc])
                except Exception as e:
                    print(f"⚠️ VISION DB SAVE SKIP: {str(e)}")

            return {
                "category": category,
                "description": extracted_desc, # Return the extracted text so the frontend can display it
                "source": "Llama 3.2 Vision",
                "confidence": 0.85
            }

        except Exception as e:
            print(f"❌ VISION LLM ERROR: {str(e)}")
            # If vision fails, we fall through to the text logic ONLY if a raw_description was also provided
            if not raw_description:
                return {"category": "Uncategorized", "source": "Vision Error", "confidence": 0.1}

    # ==========================================
    # PATH B: TEXT ONLY (YOUR EXISTING LOGIC)
    # ==========================================
    if not raw_description:
         return {"category": "Uncategorized", "source": "No Input Provided", "confidence": 0.0}

    # --- DEFENSIVE START: VECTOR DB ---
    similar = []
    try:
        if vector_db:
            similar = await run_in_threadpool(vector_db.similarity_search_with_score, raw_description, k=1)
            
            if similar and similar[0][1] > 0.85:
                return {
                    "category": similar[0][0].metadata['category'],
                    "description": raw_description,
                    "source": f"Memory Recall (Similarity: {similar[0][1]:.2f})",
                    "confidence": similar[0][1]
                }    
    except Exception as e:
        print(f"⚠️ VECTOR DB SKIP: {str(e)}")
    # --- DEFENSIVE END ---

    # ASK THE TEXT LLM
    print(f"🤖 AI Reasoning: Categorizing '{raw_description}'...")
    
    try:
        prompt = ChatPromptTemplate.from_template(
            """
            You are an expert accountant. Categorize this bank transaction description into ONE 
            standard accounting category (e.g., Software, Office Supplies, Travel, Payroll, Utility).
            Return ONLY the category name. No periods. No extra words.
            
            Transaction: {text}
            """
        )
        chain = prompt | llm
        
        response = await chain.ainvoke({"text": raw_description})
        category = response.content.strip()

        # Save to Memory
        if vector_db:
            try:
                doc = Document(
                    page_content=raw_description,
                    metadata={"category": category, "source": "ai-learned"}
                )
                await run_in_threadpool(vector_db.add_documents, [doc])
            except:
                pass
        
        return {
            "category": category,
            "description": raw_description,
            "source": "Llama 3.3 Inference",
            "confidence": 0.7 
        }

    except Exception as e:
        print(f"❌ TEXT LLM ERROR: {str(e)}")
        
        # --- FALLBACK LOGIC ---
        desc_lower = raw_description.lower()
        fallback_cat = "Uncategorized"
        if "transfer" in desc_lower: fallback_cat = "Transfer"
        elif "net" in desc_lower or "data" in desc_lower: fallback_cat = "Utilities"
        elif "food" in desc_lower or "restaurant" in desc_lower: fallback_cat = "Meals"
        
        return {
            "category": fallback_cat, 
            "description": raw_description,
            "source": "Fallback Rule", 
            "confidence": 0.1
        }
import json
import re
from datetime import datetime
from fastapi import HTTPException
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from app.core.config import settings

# Initialize Fast LLM
llm = ChatGroq(
    temperature=0, 
    model_name="llama-3.3-70b-versatile", 
    api_key=settings.GROQ_API_KEY
)

async def text_to_transactions(raw_text: str):
    """
    Uses AI to parse messy PDF text into structured JSON.
    Includes Rate Limit detection and Regex Fallback.
    """
    # Truncate to safe limit
    safe_text = raw_text[:20000] 

    print(f" Extractor: Analyzing {len(safe_text)} chars...")

    try:
        # --- FIX 1: Double Curly Braces {{ }} for JSON examples ---
        prompt = ChatPromptTemplate.from_template(
            """
            You are a Financial Data Extraction Engine.
            Your task is to extract transactions from the raw bank statement text below.

            CRITICAL ANALYSIS RULES:
            1. The text is messy. A single transaction often spans 2-4 lines.
            2. You must MERGE related lines to find the full context.
            3. DATE FORMAT: Look for dates like DD/MM/YYYY (e.g., 02/04/2026).
            4. AMOUNT FORMAT: Look for numbers with '-' (debit) or '+' (credit).
               - Example: "-400.00" -> Amount: 400.00 (Debit)
               - Example: "+52000.00" -> Amount: 52000.00 (Credit/Income)
            5. VENDOR/DESC: The name is often on the line ABOVE or BELOW the date.

            OUTPUT FORMAT:
            Return ONLY a JSON Array of objects. No Markdown.
            [{{ "date": "YYYY-MM-DD", "description": "Full Description", "amount": 0.00, "vendor": "Name" }}]

            RAW TEXT TO PROCESS:
            {text}
            """
        )

        chain = prompt | llm
        response = await chain.ainvoke({"text": safe_text})
        content = response.content.strip()
        
        # --- CLEANUP LOGIC ---
        content = content.replace("```json", "").replace("```", "").strip()
        start = content.find("[")
        end = content.rfind("]")
        
        if start != -1 and end != -1:
            content = content[start : end + 1]
            return json.loads(content)
        else:
            print(" AI did not return a valid JSON Array. Switching to Regex Fallback.")
            raise ValueError("Invalid JSON format")

    except Exception as e:
        error_msg = str(e)
        print(f" Extraction Error: {error_msg}")

        # --- 1. CATCH GROQ RATE LIMIT ---
        if "rate_limit_exceeded" in error_msg or "429" in error_msg:
            match = re.search(r"try again in ([0-9]+m[0-9]+\.?[0-9]*s)", error_msg)
            wait_time = match.group(1) if match else "a few minutes"
            
            print(f" Rate Limit Hit! Telling frontend to wait {wait_time}...")
            raise HTTPException(
                status_code=429, 
                detail=f"Groq Limit Reached. Cooldown: {wait_time}"
            )

        # --- 2. FALLBACK: REGEX (Spare Tire) ---
        print(" Switching to Regex Fallback...")
        transactions = []
        lines = raw_text.split('\n')
        
        # Regex for DD/MM/YYYY or DD-MM-YYYY
        date_pattern = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
        money_pattern = r"([\d,]+\.\d{2})"

        for line in lines:
            date_match = re.search(date_pattern, line)
            amount_matches = re.findall(money_pattern, line)
            
            if date_match and amount_matches:
                raw_date = date_match.group(0)
                
                # --- FIX 2: Convert Date to ISO (YYYY-MM-DD) ---
                # Pydantic requires YYYY-MM-DD, but banks give DD/MM/YYYY
                try:
                    # Normalize separators
                    clean_date = raw_date.replace("-", "/")
                    # Parse DD/MM/YYYY
                    date_obj = datetime.strptime(clean_date, "%d/%m/%Y")
                    # Convert to YYYY-MM-DD
                    iso_date = date_obj.strftime("%Y-%m-%d")
                except:
                    # If conversion fails, keep original (and hope for the best)
                    iso_date = raw_date

                desc = line.replace(raw_date, "").replace(amount_matches[-1], "").strip()
                desc = re.sub(r'[^\w\s]', '', desc) 
                
                transactions.append({
                    "date": iso_date, # <--- Now sending correct format
                    "description": desc or "Unknown Transaction",
                    "amount": float(amount_matches[-1].replace(",", "")),
                    "vendor": desc or "Unknown"
                })
        
        if len(transactions) > 0:
            print(f" Regex recovered {len(transactions)} items.")
            return transactions
        
        return []
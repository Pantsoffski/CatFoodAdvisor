import os
import json
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq
from duckduckgo_search import DDGS

app = FastAPI()
client = Groq(api_key=os.environ.get("GROQ_KEY"))

MODEL = "llama-3.3-70b-versatile"

class FoodRequest(BaseModel):
    breed: str
    age: int
    health: str
    food_name: str

# ==========================================
# 1. TOOLS DEFINITION (PYTHON FUNCTIONS)
# ==========================================

def search_food_database(search_query: str) -> str:
    """
    Searches the web using a custom query provided by the LLM.
    Returns snippets of text containing nutritional data.
    """
    try:
        results = DDGS().text(search_query, max_results=5) # Increased to catch additives
        
        if not results:
            return json.dumps({
                "error": f"No data found for query '{search_query}'. The LLM MUST try a different search query."
            })
        
        combined_text = " ".join([res['body'] for res in results])
        
        return json.dumps({
            "status": "success", 
            "data": combined_text
        })
        
    except Exception as e:
        return json.dumps({"error": f"Search failed: {str(e)}"})

def calculate_dry_matter(protein: float, fat: float, moisture: float, ash: float, fiber: float, calcium: float = 0.0, phosphorus: float = 0.0, taurine_mg_kg: float = 0.0) -> str:
    """
    Performs precise mathematical calculations for Dry Matter (DM), Carbohydrates (NFE), and Ca:P ratio.
    """
    if moisture >= 100:
        return json.dumps({"error": "Moisture cannot be 100% or more."})
    
    dm_factor = 100 / (100 - moisture) if moisture != 100 else 1.0
    nfe_as_fed = 100 - (protein + fat + moisture + ash + fiber)
    
    ca_p_ratio = round(calcium / phosphorus, 2) if phosphorus > 0 else 0.0
    
    results = {
        "protein_dm": round(protein * dm_factor, 2),
        "fat_dm": round(fat * dm_factor, 2),
        "ash_dm": round(ash * dm_factor, 2),
        "fiber_dm": round(fiber * dm_factor, 2),
        "nfe_carbs_dm": round(nfe_as_fed * dm_factor, 2),
        "calcium_dm": round(calcium * dm_factor, 2),
        "phosphorus_dm": round(phosphorus * dm_factor, 2),
        "ca_p_ratio": ca_p_ratio,
        "taurine_mg_kg_dm": round(taurine_mg_kg * dm_factor, 2)
    }
    return json.dumps(results)

# ==========================================
# 2. MAP TOOLS FOR THE LLM (GROQ FORMAT)
# ==========================================

tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "search_food_database",
            "description": "Searches the internet for cat food composition, including additives like Taurine, Calcium, and Phosphorus.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string", 
                        "description": "Smart query to find specific nutrients (e.g. 'Whiskas wołowina skład analityczny wapń fosfor tauryna dodatki')."
                    }
                },
                "required": ["search_query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_dry_matter",
            "description": "Calculates exact Dry Matter (DM) percentages, Ca:P ratio, and Taurine levels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "protein": {"type": "number"},
                    "fat": {"type": "number"},
                    "moisture": {"type": "number"},
                    "ash": {"type": "number"},
                    "fiber": {"type": "number"},
                    "calcium": {"type": "number", "description": "Calcium percentage (if found)"},
                    "phosphorus": {"type": "number", "description": "Phosphorus percentage (if found)"},
                    "taurine_mg_kg": {"type": "number", "description": "Taurine in mg/kg (if found)"}
                },
                "required": ["protein", "fat", "moisture", "ash", "fiber"]
            }
        }
    }
]

# ==========================================
# 3. AGENT ENGINE (API ENDPOINTS)
# ==========================================

@app.get("/")
def read_root():
    return {"status": "Cat Food Advisor Agent is online"}

@app.post("/analyze-cat-food")
def analyze_food(req: FoodRequest):
    try:
        system_prompt = (
            "You are an autonomous Veterinary Nutritionist Agent. "
            "You evaluate cat food based on European metric standards (grams, kg, percentages, mg/kg). "
            "Your tasks: Find the composition, calculate dry matter (DM), and evaluate the food. "
            "CRITICAL RULES: "
            "1. Search specifically for macronutrients AND micro-nutrients/additives (Calcium, Phosphorus, Taurine). "
            "2. If search fails, retry up to 3 times with simpler queries before stopping. "
            "3. If Moisture is missing, assume 10% for dry food or 80% for wet food. If Calcium, Phosphorus, or Taurine are missing, set them to 0 in your calculation tool. "
            "4. JUSTIFICATION RULE: Base your medical justification STRICTLY on the calculated numbers. DO NOT claim data is missing if you have populated the template with calculated values greater than 0. Address the cat's specific health issues (e.g., hyperthyroidism requires moderate iodine, high-quality protein, and avoiding excessive carbs). "
            "5. STRICT LANGUAGE RULE: Detect the language of the user's inputs. Your ENTIRE final output MUST be generated EXCLUSIVELY in that language. "
            "6. OUTPUT FORMAT RULE: You MUST output your final answer using exactly this template layout (translate headings to user's language): \n"
            "**Werdykt**: [GOOD / ACCEPTABLE / AVOID]\n"
            "**Skład w suchej masie**:\n"
            "- Białko: [X]%\n"
            "- Tłuszcz: [X]%\n"
            "- Węglowodany (NFE): [X]%\n"
            "- Wapń (Ca): [X]% | Fosfor (P): [X]% (Stosunek Ca:P: [X])\n"
            "- Tauryna: [X] mg/kg\n"
            "**Uzasadnienie**:\n"
            "[Provide 3-4 bullet points of actual medical reasoning based on the numbers above and the cat's health condition. Only complain about missing data if a specific value is exactly 0.]"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this food: '{req.food_name}' for my cat: {req.breed}, {req.age}yo, Health: {req.health}."}
        ]
        
        max_iterations = 6
        
        for _ in range(max_iterations):
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools_definition,
                tool_choice="auto",
                temperature=0.2 
            )
            
            response_message = response.choices[0].message
            
            if response_message.tool_calls:
                messages.append(response_message)
                
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    if function_name == "search_food_database":
                        function_result = search_food_database(args.get("search_query"))
                    elif function_name == "calculate_dry_matter":
                        def safe_float(val):
                            try:
                                return float(val) if val is not None else 0.0
                            except (ValueError, TypeError):
                                return 0.0
                                
                        function_result = calculate_dry_matter(
                            safe_float(args.get("protein")), 
                            safe_float(args.get("fat")), 
                            safe_float(args.get("moisture")), 
                            safe_float(args.get("ash")), 
                            safe_float(args.get("fiber")),
                            safe_float(args.get("calcium")),
                            safe_float(args.get("phosphorus")),
                            safe_float(args.get("taurine_mg_kg"))
                        )
                    else:
                        function_result = json.dumps({"error": "Unknown tool"})
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": function_result
                    })
                    
            else:
                return {"verdict": response_message.content}
                
        return {"verdict": "Error: Agent reached maximum iterations without conclusion."}
        
    except Exception as e:
        error_details = traceback.format_exc()
        print("Backend Error:", error_details) 
        raise HTTPException(status_code=500, detail=str(e))
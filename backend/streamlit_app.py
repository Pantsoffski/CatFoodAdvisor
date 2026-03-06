import streamlit as st
import os
import json
import traceback
from groq import Groq
from duckduckgo_search import DDGS
from tavily import TavilyClient

# ==========================================
# 1. AGENT CONFIGURATION & TOOLS
# ==========================================

client = Groq(api_key=os.environ.get("GROQ_KEY"))
MODEL = "llama-3.3-70b-versatile"

tavily_client = TavilyClient() if os.environ.get("TAVILY_API_KEY") else None

def search_food_database(search_query: str) -> str:
    try:
        if tavily_client:
            response = tavily_client.search(query=search_query, max_results=5)
            results = response.get("results", []) 
            if results:
                combined_text = " ".join([res['content'] for res in results])
                return json.dumps({"status": "success", "data": combined_text})
        results = DDGS().text(search_query, max_results=5)
        if not results:
            return json.dumps({"error": "No data found."})
        combined_text = " ".join([res['body'] for res in results])
        return json.dumps({"status": "success", "data": combined_text})
    except Exception as e:
        return json.dumps({"error": str(e)})

def calculate_dry_matter(protein, fat, moisture, ash, fiber, calcium=0.0, phosphorus=0.0, taurine_mg_kg=0.0):
    if moisture >= 100:
        return json.dumps({"error": "Invalid moisture"})
    dm_factor = 100 / (100 - moisture) if moisture != 100 else 1.0
    nfe_as_fed = 100 - (protein + fat + moisture + ash + fiber)
    ca_p_ratio = round(calcium / phosphorus, 2) if phosphorus > 0 else 0.0
    
    return json.dumps({
        "protein_dm": round(protein * dm_factor, 2),
        "fat_dm": round(fat * dm_factor, 2),
        "nfe_carbs_dm": round(nfe_as_fed * dm_factor, 2),
        "ca_p_ratio": ca_p_ratio,
        "taurine_dm": round(taurine_mg_kg * dm_factor, 2)
    })

# ==========================================
# 2. STREAMLIT UI SETUP
# ==========================================

st.set_page_config(page_title="Cat Food Advisor", page_icon="🐱", layout="centered")

st.title("🐱 Cat Food Advisor")
st.markdown("A smart tool to help you evaluate your cat's food quality based on veterinary guidelines.")

# Using subheaders instead of headers to reduce vertical whitespace
st.subheader("🐾 Cat Profile")

col1, col2 = st.columns(2)
with col1:
    cat_breed = st.text_input("Breed", placeholder="e.g. British Shorthair")
    cat_age = st.number_input("Age (years)", min_value=0, max_value=30, value=5)
with col2:
    # Set height to roughly match the two inputs on the left
    cat_health = st.text_area("Health Issues", placeholder="e.g. kidney disease, obesity", height=112)

st.subheader("⚙️ Settings")
unit_standard = st.radio(
    "Nutritional Standard",
    options=["European (FEDIAF)", "US (AAFCO)"],
    index=0,
    horizontal=True,
    help="Determines which veterinary guidelines to use."
)

st.subheader("🥫 Food Analysis")
food_name = st.text_input("Food Name", placeholder="Enter exact brand and flavor name...")

if st.button("Analyze Food ✨", use_container_width=True):
    if not food_name or not cat_breed:
        st.warning("Please provide at least the Cat Breed and Food Name.")
    else:
        with st.spinner("Researching and calculating... 🧪"):
            try:
                # DETOXED PROMPT
                system_prompt = (
                    "You are an expert Veterinary Nutritionist evaluating cat food.\n"
                    "Your task is to analyze the food and calculate its dry matter composition.\n"
                    "1. ALWAYS use the 'search_food_database' tool first to find Protein, Fat, Moisture, Ash, Fiber, Calcium, Phosphorus, and Taurine.\n"
                    "2. Next, ALWAYS use the 'calculate_dry_matter' tool. (If moisture is not found, input 10. If other values are missing, input 0).\n"
                    f"3. Evaluate the results based on the {unit_standard} standard.\n"
                    "4. Output your final report ENTIRELY in English using EXACTLY this format:\n\n"
                    "**Verdict**: [GOOD / ACCEPTABLE / AVOID]\n\n"
                    "**Dry Matter Composition**:\n"
                    "- Protein: [X]%\n"
                    "- Fat: [X]%\n"
                    "- Carbohydrates (NFE): [X]%\n"
                    "- Calcium (Ca): [X]% | Phosphorus (P): [X]% (Ca:P Ratio: [X])\n"
                    "- Taurine: [X] mg/kg\n\n"
                    "**Justification**:\n"
                    "- [Medical reasoning based on the calculated numbers and standard]"
                )
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze: '{food_name}' for cat: {cat_breed}, {cat_age}yo, Health: {cat_health}."}
                ]
                
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": "search_food_database",
                            "description": "Searches the web for cat food nutritional data.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "search_query": {"type": "string", "description": "The search query string."}
                                },
                                "required": ["search_query"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "calculate_dry_matter",
                            "description": "Calculates Dry Matter percentages.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "protein": {"type": "number"},
                                    "fat": {"type": "number"},
                                    "moisture": {"type": "number"},
                                    "ash": {"type": "number"},
                                    "fiber": {"type": "number"},
                                    "calcium": {"type": "number"},
                                    "phosphorus": {"type": "number"},
                                    "taurine_mg_kg": {"type": "number"}
                                },
                                "required": ["protein", "fat", "moisture", "ash", "fiber"]
                            }
                        }
                    }
                ]

                for _ in range(6):
                    response = client.chat.completions.create(
                        model=MODEL, 
                        messages=messages, 
                        tools=tools, 
                        tool_choice="auto",
                        temperature=0.1
                    )
                    msg = response.choices[0].message
                    
                    if msg.tool_calls:
                        messages.append(msg.model_dump(exclude_unset=True))
                        
                        for tool in msg.tool_calls:
                            args = json.loads(tool.function.arguments)
                            if tool.function.name == "search_food_database":
                                res = search_food_database(args.get("search_query"))
                            else:
                                res = calculate_dry_matter(
                                    args.get("protein", 0), args.get("fat", 0), 
                                    args.get("moisture", 0), args.get("ash", 0), 
                                    args.get("fiber", 0), args.get("calcium", 0), 
                                    args.get("phosphorus", 0), args.get("taurine_mg_kg", 0)
                                )
                            messages.append({"role": "tool", "tool_call_id": tool.id, "name": tool.function.name, "content": res})
                    else:
                        st.success("Analysis Complete!")
                        st.markdown(msg.content)
                        break
            except Exception as e:
                st.error(f"An error occurred: {e}")

# Disclaimer placed at the very bottom of the page
st.markdown("<br><br>", unsafe_allow_html=True)
st.caption("⚠️ **Disclaimer:** This tool provides AI-generated informational insights based on public web data and does not constitute professional veterinary or medical advice. Always consult a qualified veterinarian before making any changes to your pet's diet, especially if your cat has specific health conditions.")
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

def main():
    # Load all documents from documents.json
    doc_path = os.path.join(os.path.dirname(__file__), "data", "seed", "documents.json")
    print(f"Loading documents from {doc_path}...")
    
    with open(doc_path, "r", encoding="utf-8") as f:
        documents = json.load(f)
        
    # Convert entire list to string
    context = json.dumps(documents)
    
    # Initialize Groq LLM
    # llm = ChatGroq(
    #     model=settings.PRIMARY_LLM_MODEL,
    #     temperature=0.0,
    #     api_key=settings.PRIMARY_LLM_API_KEY
    # )
    llm = ChatGoogleGenerativeAI(
        model=settings.FALLBACK_LLM_MODEL,
        temperature=0.0,
        api_key=settings.FALLBACK_LLM_API_KEY
    )
    
    question = "how many django projects abhinav has shipped"
    
    prompt = f"""
Answer the following question based strictly on the provided JSON context.

Context:
{context}

Question: {question}

After replying to the question, give me a list of documents in the json file provided above which was useful for you to come to the answer
"""
    
    print("Sending request to Groq LLM...")
    response = llm.invoke(prompt)
    
    print("\n" + "="*50)
    print("QUESTION:", question)
    print("="*50)
    print("RESPONSE:\n")
    print(response.content)
    print("="*50)

if __name__ == "__main__":
    main()

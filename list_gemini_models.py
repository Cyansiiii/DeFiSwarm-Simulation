import google.generativeai as genai

GEMINI_API_KEY = "AIzaSyBkB3H5uc6vmDEp6DGUv33EEohiUjVA-Kg"
genai.configure(api_key=GEMINI_API_KEY)
 
print("Available Gemini models:")
for m in genai.list_models():
    print(f"- {m.name}") 
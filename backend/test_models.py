import os
import sys
import traceback
from google import genai
from google.genai import types

print("🚀 Starting Gemini Model Test...")
print("Python version:", sys.version)

try:
    # Vertex AI setup
    print("📋 Setting up environment variables...")
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "watchful-bonus-459710-k9")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    
    print("✅ Environment variables set")
    print(f"   Project: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
    print(f"   Location: {os.environ.get('GOOGLE_CLOUD_LOCATION')}")
    
    print("🔌 Initializing Gemini client...")
    client = genai.Client(vertexai=True)
    print("✅ Client initialized successfully")
    
except Exception as e:
    print(f"❌ Failed to initialize client: {e}")
    print("Full traceback:")
    traceback.print_exc()
    sys.exit(1)

def test_models():
    """Test different Gemini model names to find what works"""
    
    print("\n🧪 Starting model tests...")
    
    models_to_test = [
        # Most likely to work first
        "gemini-1.5-flash",
        "gemini-1.5-flash-001", 
        "gemini-1.5-pro",
        "gemini-1.5-pro-001",
        # Newer models (might not be available)
        "gemini-2.0-flash-001",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-2.5-flash-001",
    ]
    
    test_prompt = "Hello, respond with just 'WORKING'"
    
    working_models = []
    
    for i, model_name in enumerate(models_to_test, 1):
        try:
            print(f"\n📊 Test {i}/{len(models_to_test)}: {model_name}")
            print("   Sending request...")
            
            # Use simple generate_content instead of streaming
            response = client.models.generate_content(
                model=model_name,
                contents=[types.Part(text=test_prompt)],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    top_p=0.1,
                    max_output_tokens=50,
                )
            )
            
            if response and hasattr(response, 'text') and response.text:
                print(f"✅ SUCCESS: {model_name}")
                print(f"   Response: '{response.text.strip()}'")
                working_models.append(model_name)
            else:
                print(f"❌ FAILED: {model_name} - No response text")
                
        except Exception as e:
            print(f"❌ FAILED: {model_name}")
            print(f"   Error: {str(e)}")
            # Print first line of error for debugging
            error_msg = str(e).split('\n')[0]
            print(f"   Details: {error_msg}")
    
    print(f"\n" + "="*50)
    print(f"🎯 RESULTS SUMMARY:")
    print(f"   Total tested: {len(models_to_test)}")
    print(f"   Working: {len(working_models)}")
    print(f"   Failed: {len(models_to_test) - len(working_models)}")
    
    if working_models:
        print(f"\n🎉 WORKING MODELS:")
        for i, model in enumerate(working_models, 1):
            print(f"   {i}. ✅ {model}")
        
        best_model = working_models[0]
        print(f"\n🚀 RECOMMENDED MODEL TO USE:")
        print(f"   {best_model}")
        print(f"\n📋 COPY THIS TO YOUR MAIN CODE:")
        print(f'   model="{best_model}"')
        return best_model
    else:
        print(f"\n❌ NO WORKING MODELS FOUND!")
        print("   This suggests an authentication or project setup issue.")
        return None

if __name__ == "__main__":
    print("🔍 Testing Gemini Models on Your Vertex AI Setup...")
    print("=" * 60)
    
    try:
        working_model = test_models()
        
        if working_model:
            print(f"\n🎯 SUCCESS! Use this model in your FastAPI code:")
            print(f"   Replace 'gemini-2.5-flash' with '{working_model}'")
        else:
            print(f"\n🆘 TROUBLESHOOTING STEPS:")
            print("   1. Check Google Cloud authentication")
            print("   2. Verify project ID: watchful-bonus-459710-k9")
            print("   3. Check Vertex AI API is enabled")
            print("   4. Try: gcloud auth application-default login")
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
    
    print(f"\n✅ Test completed.")
    input("Press Enter to exit...")
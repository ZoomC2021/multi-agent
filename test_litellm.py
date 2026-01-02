import os
from dotenv import load_dotenv
from litellm import completion

# Load environment
load_dotenv()

# Ensure keys are set as the main script does
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

model = "gemini/gemini-3-pro-preview"
print(f"Testing LiteLLM with model: {model}")
print(f"GOOGLE_API_KEY set: {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")

try:
    response = completion(
        model=model, messages=[{"role": "user", "content": "Hello, are you working?"}]
    )
    print("Success!")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Failed with {model}: {e}")

    # Try fallback
    fallback = "gemini/gemini-1.5-pro"
    print(f"\nRetrying with fallback: {fallback}")
    try:
        response = completion(
            model=fallback, messages=[{"role": "user", "content": "Hello, are you working?"}]
        )
        print("Success with fallback!")
        print(response.choices[0].message.content)
    except Exception as e2:
        print(f"Failed with fallback {fallback}: {e2}")

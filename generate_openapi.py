import json
import os

# Set dummy values for the secret key for openapi generation
os.environ["SUBSCRIPTION_SECRET_KEY"] = "dummy_key_for_openapi_generation"
os.environ["INTERNAL_API_KEY"] = "dummy_key"

from server import app

def generate_openapi_spec():
    """
    Generates the OpenAPI specification for the FastAPI application.
    """
    openapi_schema = app.openapi()
    with open("openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)

if __name__ == "__main__":
    generate_openapi_spec()
    print("OpenAPI specification generated successfully as openapi.json")

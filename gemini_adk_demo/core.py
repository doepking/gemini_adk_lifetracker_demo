import os
import vertexai

vertexai.init(
    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    location=os.environ.get("GOOGLE_CLOUD_LOCATION"),
)

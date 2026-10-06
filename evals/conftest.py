import os

# The offline tier never talks to LangSmith or any model provider.
os.environ["LANGSMITH_TRACING"] = "false"

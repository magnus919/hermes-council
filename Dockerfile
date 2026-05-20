FROM python:3.12-slim

# Install openai library (only dependency)
RUN pip install --no-cache-dir openai

# Copy the demo runner
COPY docker/council_demo.py /council_demo.py

ENTRYPOINT ["python3", "/council_demo.py"]

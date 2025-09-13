from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from openai import OpenAI
import json
import os
import re
from dotenv import load_dotenv
import time

load_dotenv()
Client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Azure setup
endpoint = 'https://aiformfilling-doc-ai.cognitiveservices.azure.com/'
key = os.getenv('AZURE_KEY')
client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
res = []
def extract_and_generate_schema(file_path):
    AzurestartTime = time.time()
    # Analyze document with Azure
    with open(file_path, "rb") as f:
        poller = client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=f,
            content_type="image/jpeg"
        )
    result = poller.result()
    endTime =  time.time() - AzurestartTime
    res.append(endTime)

    # Collect all lines from the document
    lines = []
    for page in result.pages:
        for line in page.lines:
            lines.append(line.content)

    # Prompt OpenAI to create a schema from the lines
    openApiStart = time.time()
    messages = [
        {
            'role': 'system',
            'content': (
                "You are an assistant that takes lines from a scanned form and reconstructs a JSON form schema. "
                "Return ONLY valid JSON in your response. For each section of the form, have a value section that will be filled in later. "
                "Make sure to adjust for questions that require select-if questions and for questions that have conditions. "
                "Each field should have these sections: type, required, options, accessibility, and value."
            )
        },
        {
            'role': 'user',
            'content': (
                "Here are the lines from the form:\n" +
                "\n".join(lines) +
                "\nReturn ONLY valid JSON. Instead of deeply nested objects, represent each field as a flat entry in a 'fields' array. "
"Each field object should include: label, section (if applicable), type, required, options (if any), accessibility, and value (empty for now). "
"Organize sections using a 'section' field, but keep each field as its own object."
            )
        }
    ]

    response = Client.chat.completions.create(
        model='gpt-4.1-mini-2025-04-14',
        messages=messages,
        max_tokens=2048,
        temperature=0
    )
    answer = response.choices[0].message.content
    endAP =  time.time() - openApiStart
    res.append(endAP)

    
    if answer.strip().startswith("```"):
        answer = re.sub(r"^```[a-zA-Z]*\n?", "", answer.strip())
        answer = re.sub(r"\n?```$", "", answer.strip())

    try:
        structured = json.loads(answer)
        return structured
    except Exception:
        return None
    
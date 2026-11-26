import os

from openai import OpenAI

client = OpenAI(api_key=os.environ["BEDROCK_API_KEY"],
                base_url="https://bedrock-mantle.us-east-1.api.aws/openai/v1")

instructions = r"""
thematic analysis:
code/cluster user interactions
categorize into user behavior

good luck
"""
input = r"""


"""

file_path = r"C:\Users\alexc\Downloads\data.csv"
file_data = ""
with open(file_path, "r", encoding="utf-8") as f:
    file_data = f.read()

def chat():
    response = client.responses.create(
        model="openai.gpt-5.6-sol",
        instructions=instructions,
        input=file_data,
        tools=[{"type": "web_search", "external_web_access": False}],
        max_output_tokens=10000,
        store=False,
        reasoning={"effort": "medium"}
    )
    reply = response.output_text

    return print (reply)

chat()
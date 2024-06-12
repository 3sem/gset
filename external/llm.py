import os
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

api_key = os.environ["MISTRAL_API_KEY"]
client = MistralClient(api_key=api_key)


def get_embeddings(prompt, model="codestral-latest"):
    return client.embeddings(model=model, input=prompt)


def chat(content="", model="codestral-latest", verbose=False):
    messages = [
        ChatMessage(role="user", content=content)
    ]
    chat_response = client.chat(
        model=model,
        messages=messages
    )
    if verbose:
        print(chat_response.choices[0].message.content)
    return chat_response.choices


def prompt_completion( prompt, suffix, model="codestral-latest", verbose=False):
    model = "codestral-latest"
    prompt = "def fibonacci(n: int):"
    suffix = "n = int(input('Enter a number: '))\nprint(fibonacci(n))"

    response = client.completion(
        model=model,
        prompt=prompt,
        suffix=suffix,
    )
    if verbose:
        print(
            f"""
        {prompt}
        {response.choices[0].message.content}
        {suffix}
        """
        )
    return prompt, response.choices, suffix
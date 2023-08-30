import openai


class OpenAIAPI:
    def __init__(self, api_key):
        openai.api_key = api_key

    def generate_summary(self, content):
        prompt_summary = f"Summarize the following content in one sentence:\n{content}"
        messages = [
            {
                "role": "system",
                "content": "You are an AI assistant helping to summarize projects.",
            },
            {"role": "user", "content": prompt_summary},
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0301",
            messages=messages,
            max_tokens=50,
            temperature=0.0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        return response.choices[0].message['content'].strip()

    def generate_title(self, summary):
        prompt_title = (
            f"Provide accurate short title in less than 4 words, "
            f"do not mention word Project, Model or System"
            f"in the end of title: \nSummary: {summary}"
        )
        messages = [
            {
                "role": "system",
                "content": "You are an AI assistant helping to generate accurate short titles.",
            },
            {"role": "user", "content": prompt_title},
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0301",
            messages=messages,
            max_tokens=10,
            n=1,
            temperature=0.4,
            top_p=1,
            frequency_penalty=0.0,
            presence_penalty=0,
        )
        return response.choices[0].message['content'].strip().rstrip('.')

import openai


class OpenAIAPI:
    def __init__(self, api_key):
        openai.api_key = api_key

    def generate_summary(self, content):
        prompt_summary = f"Summarize the following content in two sentences:\n{content}"
        # print("Content readme:", content)
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
            max_tokens=100,
            temperature=0.0,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        return response.choices[0].message['content'].strip()

    def generate_multiple_titles(self, summary):
        prompt_title = f"As an AI prompt generator for GPT-4, I will assist in generating concise titles. Please provide a summary of the content or topic for which you need a title. Make sure the title is less than 4 words and does not include words like 'Project', 'Model', or 'System' at the end. Use clear and concise language, follow proper grammar and spelling, and aim for unique and creative titles : \nSummary: {summary}"
        # print("Summary:", summary)
        messages = [
            {
                "role": "system",
                "content": "You are an AI assistant helping to generate concise titles.",
            },
            {"role": "user", "content": prompt_title},
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0301",
            messages=messages,
            max_tokens=6,
            n=5,
            temperature=0.9,
            top_p=0.8,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )
        titles = [
            choice.message['content'].strip().rstrip('.') for choice in response.choices
        ]
        unique_titles = list(set(titles))
        return unique_titles

    def evaluate_and_revise_titles(self, titles):
        # Initialize scores (this is a simplified example)
        scores = {}
        for title in titles:
            score = 0
            if len(title.split()) <= 4:
                score += 2 * 0.6  # Weight of 0.6
            if title.isalpha():
                score += 1 * 0.4  # Weight of 0.4
            scores[title] = score
        best_title = max(scores, key=scores.get)

        feedback = f"The best title among the generated ones is '{best_title}' with a score of {scores[best_title]}."

        revised_title = best_title

        return feedback, revised_title

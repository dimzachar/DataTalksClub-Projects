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
    
    def generate_multiple_titles(self, summary):
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
            max_tokens=6,
            n=3,  # Generate 3 titles
            temperature=0.3,
            top_p=0.8,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )
        titles = [choice.message['content'].strip().rstrip('.') for choice in response.choices]
        return titles


    # def generate_title(self, summary):
    #     prompt_title = (
    #         f"Provide accurate short title in less than 4 words, "
    #         f"do not mention word Project, Model or System"
    #         f"in the end of title: \nSummary: {summary}"
    #     )
    #     messages = [
    #         {
    #             "role": "system",
    #             "content": "You are an AI assistant helping to generate accurate short titles.",
    #         },
    #         {"role": "user", "content": prompt_title},
    #     ]
    #     response = openai.ChatCompletion.create(
    #         model="gpt-3.5-turbo-0301",
    #         messages=messages,
    #         max_tokens=6,
    #         n=1,
    #         temperature=0.4,
    #         top_p=1,
    #         frequency_penalty=0.0,
    #         presence_penalty=0,
    #     )
    #     return response.choices[0].message['content'].strip().rstrip('.')
    def evaluate_and_revise_titles(self, titles):
        # Initialize scores (this is a simplified example)
        scores = {}
        
        # Scoring Mechanism
        for title in titles:
            score = 0
            if len(title.split()) <= 4:  # Length
                score += 2
            if title.isalpha():  # Clarity
                score += 1
            scores[title] = score
        
        # Feedback Generation
        best_title = max(scores, key=scores.get)
        feedback = f"The best title among the generated ones is '{best_title}' with a score of {scores[best_title]}."
        
        # Revision (Capitalizing the best title)
        revised_title = best_title.capitalize()
        
        return feedback, revised_title
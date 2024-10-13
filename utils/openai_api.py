import re
import random

from openai import OpenAI


class OpenAIAPI:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def build_prompt(self, project_url, summary):
        prompt_template = """
As an AI specializing in creating engaging and descriptive titles for software projects, your task is to generate 3 unique titles for a GitHub project. Use the following guidelines:

1. Analyze the project URL and summary to extract key information.
2. Create titles that are concise (3-5 words) and captivating.
3. Use dynamic verbs and specific nouns related to the project's function.
5. Avoid generic terms like "Smart", "Intelligent", "Assistant", "Hub", or "Companion" unless central to the project.
6. Consider using a two-part structure with a colon or dash for clarity.
7. Ensure the title clearly communicates the project's main purpose or problem it solves.

Project URL: {url}
Project Summary: {summary}

Generate 5 distinct titles, each on a new line:
""".strip()
        return prompt_template.format(url=project_url, summary=summary)

    def llm(self, prompt, model='gpt-4o-mini', max_tokens=150):
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content, response.usage
        except Exception as e:
            print(f"An error occurred: {e}")
            return None, None

    def generate_summary(self, content):
        prompt_summary = f"Summarize the following GitHub project content in two sentences, focusing on its main purpose and key features:\n{content}"
        summary, _ = self.llm(prompt_summary, max_tokens=100)
        return summary.strip() if summary else ""

    def generate_multiple_titles(self, project_url, summary):
        title_prompt = self.build_prompt(project_url, summary)
        titles, _ = self.llm(title_prompt, max_tokens=150)
        if titles:
            titles_list = [
                re.sub(r'^[-\d]+\.\s*|\s*-\s*', '', title.strip())
                for title in titles.split('\n')
                if title.strip()
            ]
            return list(set(filter(None, titles_list)))
        return []

    def evaluate_title(self, title, project_url, summary):
        score = 0
        word_count = len(title.split())

        if 3 <= word_count <= 5:
            score += 2
        elif word_count < 3 or word_count > 5:
            score -= 1

        keywords = re.findall(r'\w+', project_url.lower() + ' ' + summary.lower())
        for word in title.lower().split():
            if word in keywords:
                score += 1

        generic_terms = ['smart', 'intelligent', 'assistant', 'hub', 'companion']
        for term in generic_terms:
            if term in title.lower():
                score -= 1

        if ':' in title or '-' in title:
            score += 1

        return score

    def evaluate_and_revise_titles(self, titles, project_url, summary):
        scores = {
            title: self.evaluate_title(title, project_url, summary) for title in titles
        }
        best_title = max(scores, key=scores.get)

        if scores[best_title] < 3:
            new_titles = self.generate_multiple_titles(project_url, summary)
            new_scores = {
                title: self.evaluate_title(title, project_url, summary)
                for title in new_titles
            }
            combined_scores = {**scores, **new_scores}
            best_title = max(combined_scores, key=combined_scores.get)

        feedback = (
            f"The best title is '{best_title}' with a score of {scores[best_title]}."
        )
        return feedback, best_title

    def process_project(self, project_url, content):
        summary = self.generate_summary(content)
        titles = self.generate_multiple_titles(project_url, summary)
        feedback, best_title = self.evaluate_and_revise_titles(
            titles, project_url, summary
        )
        return best_title

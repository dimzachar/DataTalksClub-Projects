import string

import nltk
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from nltk.stem import WordNetLemmatizer
from wordcloud import WordCloud
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')


class EDAAnalysis:
    def __init__(self, data):
        self.data = data

    def preprocess_text(self, text):
        lemmatizer = WordNetLemmatizer()
        stop_words = set(stopwords.words('english'))

        text = text.lower()
        text = text.translate(str.maketrans('', '', string.punctuation))
        word_tokens = word_tokenize(text)

        return [
            lemmatizer.lemmatize(word) for word in word_tokens if word not in stop_words
        ]

    def calculate_word_frequency(self, processed_titles):
        all_words = [word for words in processed_titles for word in words]
        return pd.Series(all_words).value_counts()

    def generate_wordcloud(self, processed_titles):
        all_words2 = ' '.join([' '.join(words) for words in processed_titles])
        return WordCloud(
            width=1000, height=500, max_words=100, min_font_size=10
        ).generate(all_words2)

    def plot_histogram(self, column):
        sns.histplot(self.data[column])
        plt.show()

    def plot_correlation_matrix(self):
        corr = self.data.corr()
        sns.heatmap(corr, annot=True)
        plt.show()

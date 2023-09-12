import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import string
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from wordcloud import WordCloud
import nltk

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

class EDAAnalysis:
    def __init__(self, data):
        self.data = data  # Now accepts DataFrame directly

    def preprocess_text(self, text):
        lemmatizer = WordNetLemmatizer()
        stop_words = set(stopwords.words('english'))

        text = text.lower()
        text = text.translate(str.maketrans('', '', string.punctuation))
        word_tokens = word_tokenize(text)

        return [lemmatizer.lemmatize(word) for word in word_tokens if word not in stop_words]

    def calculate_word_frequency(self, processed_titles):
        all_words = [word for words in processed_titles for word in words]
        return pd.Series(all_words).value_counts()

    def generate_wordcloud(self, processed_titles):
        all_words2 = ' '.join([' '.join(words) for words in processed_titles])
        return WordCloud(width=1000, height=500).generate(all_words2)

    def plot_histogram(self, column):
        sns.histplot(self.data[column])
        plt.show()

    def plot_correlation_matrix(self):
        corr = self.data.corr()
        sns.heatmap(corr, annot=True)
        plt.show()

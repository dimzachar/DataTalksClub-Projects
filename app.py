import streamlit as st
import pandas as pd
import os
from src.eda_analysis import EDAAnalysis  # Import the EDAAnalysis class from eda_analysis.py
import matplotlib.pyplot as plt
# Function to load data based on selected courses and years
def load_data(selected_courses, selected_years):
    dfs = []
    for course in selected_courses:
        for year in selected_years:
            path = f"./Data/{course}/{year}/data.csv"
            if os.path.exists(path):
                print(f"Loading data from {path}")  # Debug print
                dfs.append(pd.read_csv(path))
            else:
                print(f"File not found: {path}")  # Debug print
    return pd.concat(dfs, ignore_index=True) if dfs else None

# Streamlit app
st.title('DataTalksClub Projects EDA')

# Multiselect to select course(s)
selected_courses = st.multiselect('Select course(s):', ['dezoomcamp', 'mlopszoomcamp', 'mlzoomcamp'])

# Multiselect to select year(s)
selected_years = st.multiselect('Select year(s):', ['2021', '2022', '2023'])

# Load data based on selected courses and years
if selected_courses and selected_years:
    data = load_data(selected_courses, selected_years)
    if data is not None:
        print("Data loaded successfully.")  # Debug print
        # Initialize EDAAnalysis class
        analysis = EDAAnalysis(data)

        # Text preprocessing for project titles
        data['project_title'] = data['project_title'].astype(str)
        data['processed_titles'] = data['project_title'].apply(analysis.preprocess_text)

        # Word frequency calculation
        word_freq = analysis.calculate_word_frequency(data['processed_titles'])
        st.write('Word Frequency:', word_freq)

        # Checkbox to show data
        if st.checkbox('Show data'):
            st.write(data)
            
        # Top 10 Most Frequent Project Titles
        st.header('Top 10 Most Frequent Project Titles')
        top_titles = data['project_title'].value_counts()[:20]
        for i, (title, freq) in enumerate(top_titles.items()):
            st.write(f"{i+1}. {title}: {freq}")
        fig, ax = plt.subplots()
        top_titles.plot(kind='barh', ax=ax, color='darkseagreen', edgecolor='black')
        ax.set_title('Top 10 Most Frequent Project Titles')
        ax.set_xlabel('Frequency')
        ax.set_ylabel('Project Titles')
        ax.invert_yaxis()
        st.pyplot(fig)
        
        st.header('Top 20 Most Frequent Words')
        top_words = word_freq[:30]
        for i, (word, freq) in enumerate(top_words.items()):
            st.write(f"{i+1}. {word}: {freq}")
        fig, ax = plt.subplots()
        top_words.plot(kind='bar', ax=ax, color='darkseagreen', edgecolor='black')
        ax.set_title('Top 20 Most Frequent Words in Project Titles')
        ax.set_xlabel('Words')
        ax.set_ylabel('Frequency')
        ax.tick_params(axis='x', rotation=45)
        st.pyplot(fig)
        
        st.header('Word Cloud')
        wordcloud = analysis.generate_wordcloud(data['processed_titles'])
        st.image(wordcloud.to_array())
        
        
        # Deployment Type Distribution
        st.header('Deployment Type Distribution')
        deployment_types = data['Deployment Type'].value_counts()
        fig, ax = plt.subplots()
        deployment_types.plot(kind='bar', ax=ax, color='darkseagreen', edgecolor='black')
        ax.set_title('Deployment Type Distribution')
        ax.set_xlabel('Deployment Type')
        ax.set_ylabel('Frequency')
        st.pyplot(fig)



    else:
        st.write("No data loaded.")
else:
    st.write("Please select at least one course and one year to load data.")

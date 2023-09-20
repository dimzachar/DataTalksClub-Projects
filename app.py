import os
import warnings

import pandas as pd
import seaborn as sns
import streamlit as st
import matplotlib.pyplot as plt
from pandas.api.types import (
    is_object_dtype,
    is_numeric_dtype,
    is_categorical_dtype,
    is_datetime64_any_dtype,
)

from src.eda_analysis import EDAAnalysis

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="DataTalksClub", page_icon=":cookie:", initial_sidebar_state="expanded"
)


def set_dark_theme_style():
    # plt.style.use('dark_background')

    plt.rcParams['figure.facecolor'] = '#323e45'
    plt.rcParams['axes.facecolor'] = '#323e45'
    plt.rcParams['axes.edgecolor'] = '#8FBC8F'
    plt.rcParams['axes.labelcolor'] = '#ffffff'
    plt.rcParams['xtick.color'] = '#ffffff'
    plt.rcParams['ytick.color'] = '#ffffff'
    plt.rcParams['text.color'] = '#ffffff'


set_dark_theme_style()


@st.cache_data
# Function to load data based on selected courses and years
def load_data(selected_courses, selected_years):
    dfs = []
    for course in selected_courses:
        for year in selected_years:
            path = f"./Data/{course}/{year}/data.csv"
            if os.path.exists(path):
                print(f"Loading data from {path}")
                df = pd.read_csv(path)
                df['Course'] = course
                df['Year'] = year
                dfs.append(df)
            else:
                print(f"File not found: {path}")
    return pd.concat(dfs, ignore_index=True) if dfs else None


st.title(
    'Interactive [DataTalksClub](https://github.com/DataTalksClub) Course Projects Dashboard'
)


course_options = ['dezoomcamp', 'mlopszoomcamp', 'mlzoomcamp']
year_options = ['2021', '2022', '2023']

# Multiselect to select course(s) with all options selected by default
selected_courses = st.multiselect(
    'Select course(s):', course_options, default=course_options
)

# Multiselect to select year(s) with all options selected by default
selected_years = st.multiselect('Select year(s):', year_options, default=year_options)

# Add a search bar instead of filter -> change to filter
# search_term = st.text_input('Search by Project Title:', '')
# # Multiselect to select course(s)
# selected_courses = st.multiselect(
#     'Select course(s):', ['dezoomcamp', 'mlopszoomcamp', 'mlzoomcamp']
# )

# # Multiselect to select year(s)
# selected_years = st.multiselect('Select year(s):', ['2021', '2022', '2023'])


def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    filter_container = st.container()

    with filter_container:
        
        available_columns = [col for col in df.columns if col not in ['Course', 'Year']]
        to_filter_columns = st.multiselect(
            "Select columns to filter", available_columns, default=available_columns
        )
        col1, col2 = st.columns(2) 
    
        hide_unknowns = col1.checkbox("Hide Unknown Titles")
        show_only_unknowns = col2.checkbox("Show only Unknown Titles")
        

        if hide_unknowns and show_only_unknowns:
            st.warning("You cannot select both options at the same time.")
            df_filtered = df.copy()
        elif hide_unknowns:
            df_filtered = df[df['project_title'] != 'Unknown']
        elif show_only_unknowns:
            df_filtered = df[df['project_title'] == 'Unknown']
        else:
            df_filtered = df.copy()

        for column in to_filter_columns:
            try:
                _ = {x for x in df[column]}
            except TypeError:
                continue

            left, right = st.columns((1, 20))
            left.write("↳")
            if (
                is_categorical_dtype(df_filtered[column])
                or df_filtered[column].nunique() < 10
            ):
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df_filtered[column].unique(),
                    default=list(df_filtered[column].unique()),
                )
                df_filtered = df_filtered[df_filtered[column].isin(user_cat_input)]
            elif is_numeric_dtype(df_filtered[column]):
                _min = float(df_filtered[column].min())
                _max = float(df_filtered[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    _min,
                    _max,
                    (_min, _max),
                    step=step,
                )
                df_filtered = df_filtered[df_filtered[column].between(*user_num_input)]
            else:
                user_text_input = right.text_input(f"Substring or regex in {column}")
                case_sensitive = right.checkbox(
                    'Case Sensitive', value=False, key=f"case_sensitive_{column}"
                )

                if user_text_input:
                    mask = df_filtered[column].str.contains(
                        user_text_input, case=case_sensitive, na=False
                    )
                    df_filtered = df_filtered[mask]

    return df_filtered


# Load data based on selected courses and years
if selected_courses and selected_years:
    data = load_data(selected_courses, selected_years)
    if data is not None:
        print("Data loaded successfully.")

        analysis = EDAAnalysis(data)

        data['project_title'] = data['project_title'].astype(str)
        data['processed_titles'] = data['project_title'].apply(analysis.preprocess_text)

        # if search_term:
        #     data = data[data['project_title'].str.contains(search_term, case=False)]
        # else:
        #     data = data
        data = filter_dataframe(data)

        st.write(f"Number of projects loaded: {data.shape[0]}")

        st.dataframe(
            data,
            column_config={
                "project_url": st.column_config.LinkColumn("Project URL"),
            },
            hide_index=True,
        )

        if not data.empty:
            csv = data.to_csv(index=False).encode('utf-8')
            if st.download_button(
                label="Download CSV",
                data=csv,
                file_name='data.csv',
                mime='text/csv',
                key='download-csv',
            ):
                st.write('Download Completed!')

        word_freq = analysis.calculate_word_frequency(data['processed_titles'])

        # Top 10 Most Frequent Project Titles
        st.header('Top 10 Most Frequent Project Titles')
        try:
            top_titles = data['project_title'].value_counts()[:10]
            fig, ax = plt.subplots()
            top_titles.plot(kind='barh', ax=ax, color='darkseagreen', edgecolor='black')
            ax.set_title('Top 10 Most Frequent Project Titles')
            ax.set_xlabel('Frequency')
            ax.set_ylabel('Project Titles')
            ax.invert_yaxis()
            st.pyplot(fig)
        except Exception as e:
            st.write(
                "An error occurred while plotting the most frequent project titles."
            )

        # Top 10 Most Frequent Words
        st.header('Top 10 Most Frequent Words')
        try:
            top_words = word_freq[:10]
            fig, ax = plt.subplots()
            top_words.plot(kind='bar', ax=ax, color='darkseagreen', edgecolor='black')
            ax.set_title('Top 10 Most Frequent Words in Project Titles')
            ax.set_xlabel('Words')
            ax.set_ylabel('Frequency')
            ax.tick_params(axis='x', rotation=45)
            st.pyplot(fig)
        except Exception as e:
            st.write("An error occurred while plotting the most frequent words.")

        # Word Cloud
        st.header('WordCloud')
        try:
            wordcloud = analysis.generate_wordcloud(data['processed_titles'])
            st.image(wordcloud.to_array(), use_column_width=True)
        except Exception as e:
            st.write("An error occurred while generating the word cloud.")

        # Deployment Type Distribution
        st.header('Deployment Type Distribution')
        try:
            deployment_types = data['Deployment Type'].value_counts()
            fig, ax = plt.subplots()
            deployment_types.plot(
                kind='barh', ax=ax, color='darkseagreen', edgecolor='black'
            )
            ax.set_title('Deployment Type Distribution')
            ax.set_xlabel('Deployment Type')
            ax.set_ylabel('Frequency')
            ax.invert_yaxis()
            st.pyplot(fig)
        except Exception as e:
            st.write(
                "An error occurred while plotting the deployment type distribution."
            )

        # Plot the distribution of cloud providers
        st.header('Cloud Provider Distribution')
        try:
            cloud_provider_counts = data['Cloud'].value_counts()
            fig, ax = plt.subplots()
            cloud_provider_counts.plot(
                kind='bar', ax=ax, color='darkseagreen', edgecolor='black'
            )
            ax.set_title('Cloud Provider Distribution')
            ax.set_xlabel('Cloud Provider')
            ax.set_ylabel('Frequency')
            st.pyplot(fig)
        except Exception as e:
            st.write(
                "An error occurred while plotting the cloud provider distribution."
            )

        course_counts = data['Course'].value_counts()

        palette = sns.color_palette("pastel", len(course_counts.index))
        course_order = course_counts.index.tolist()

        fig, ax = plt.subplots()
        ax.pie(
            course_counts,
            labels=course_counts.index,
            startangle=90,
            autopct='%1.1f%%',
            wedgeprops=dict(width=0.2),
            colors=palette,
        )
        ax.set_title("Distribution of Projects Across Different Courses")
        st.pyplot(fig)

        fig, ax = plt.subplots(figsize=(10, 6))
        order_years = sorted(data['Year'].unique())
        sns.countplot(
            x='Year',
            hue='Course',
            data=data,
            palette=palette,
            ax=ax,
            order=order_years,
            hue_order=course_order,
        )
        ax.set_title('Distribution of Projects by Year for Each Course')
        st.pyplot(fig)

        fig, ax = plt.subplots(figsize=(10, 6))
        sns.countplot(
            x='Cloud',
            hue='Course',
            data=data,
            palette=palette,
            ax=ax,
            hue_order=course_order,
        )
        ax.set_title('Distribution in Different Clouds by Course')
        st.pyplot(fig)

        fig, ax = plt.subplots(figsize=(10, 6))
        sns.countplot(
            x='Deployment Type',
            hue='Course',
            data=data,
            palette=palette,
            ax=ax,
            hue_order=course_order,
        )
        ax.set_title('Distribution in Different Deployment Types by Course')
        st.pyplot(fig)

    else:
        st.write("No data loaded.")
else:
    st.write("Please select at least one course and one year to load data.")

# Add donation links in sidebar
st.sidebar.write("Help Keep This Service Running")
st.sidebar.markdown(
    "<a href='https://www.paypal.com/donate/?hosted_button_id=LR3PQYHZY4CJ4'><img src='https://www.paypalobjects.com/digitalassets/c/website/marketing/apac/C2/logos-buttons/optimize/26_Yellow_PayPal_Pill_Button.png' width='128'></a>",
    unsafe_allow_html=True,
)


st.sidebar.write("Connect with me")
st.sidebar.markdown(
    "<a href='https://www.linkedin.com/in/zacharenakis'><img src='https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png' width='32'></a>",
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    "<a href='https://zacharenakis.super.site'><img src='https://img.icons8.com/external-vectorslab-flat-vectorslab/53/null/external-Favorite-Website-web-and-marketing-vectorslab-flat-vectorslab.png' width='32'></a>",
    unsafe_allow_html=True,
)

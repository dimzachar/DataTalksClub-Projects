import os
import warnings

import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
import plotly.graph_objects as go
from pandas.api.types import (
    is_object_dtype,
    is_numeric_dtype,
    is_categorical_dtype,
    is_datetime64_any_dtype,
)
from streamlit_lottie import st_lottie
import requests
import urllib.parse

from src.eda_analysis import EDAAnalysis

warnings.filterwarnings("ignore")


st.set_page_config(
    page_title="DataTalksClub", page_icon=":cookie:", initial_sidebar_state="expanded"
)


background_svg_url = "https://raw.githubusercontent.com/dimzachar/DataTalksClub-Projects/master/blob-scene-haikei.svg?sanitize=true"

css_style = f"""
<style>
    body, .fullScreenFrame, .stApp {{
        background-image: url({background_svg_url});
        background-size: cover;
        background-repeat: no-repeat;
    }}
</style>
"""

st.markdown(css_style, unsafe_allow_html=True)

sidebar_css = """
<style>
    .sidebar .sidebar-content {
        background-color: #001220;
    }
</style>
"""
st.markdown(sidebar_css, unsafe_allow_html=True)


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


st.sidebar.title(
    'Interactive [DataTalksClub](https://github.com/DataTalksClub) Course Projects Dashboard'
)
left_co, cent_co, last_co = st.columns(3)
with left_co:
    st.image("dtc_logo.png", width=650)


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

        hide_unknowns = col1.checkbox("Hide Unknown Titles", value=True)
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

        # Define a function to apply the background color
        def background_color(val):
            return f'background-color: #001220'

        # Apply the background color to the DataFrame
        styled_data = data.style.applymap(background_color)

        # Display the styled DataFrame in Streamlit
        st.dataframe(
            styled_data,
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

        ########
        # PLOT
        #####################################################
        # Settings
        word_freq = analysis.calculate_word_frequency(data['processed_titles'])
        top_titles = data['project_title'].value_counts()[:10]
        top_words = word_freq[:10]
        course_counts = data['Course'].value_counts()
        deployment_types = data['Deployment Type'].value_counts()
        cloud_provider_counts = data['Cloud'].value_counts()

        palette = sns.color_palette("cubehelix", len(course_counts.index))
        course_order = course_counts.index.tolist()
        # Convert Seaborn palette to a list of colors
        palette_colors = sns.color_palette(palette, len(course_order)).as_hex()
        #####################################################

        ################################
        # Word Cloud
        ################################
        st.header('WordCloud')
        try:
            wordcloud = analysis.generate_wordcloud(data['processed_titles'])
            st.image(wordcloud.to_array(), use_column_width=True)
        except Exception as e:
            st.write("An error occurred while generating the word cloud.")

        #################################
        # Plot Top 10 Most Frequent Project Titles
        ################################

        try:
            # Initialize Plotly figure for the horizontal bar chart
            fig = go.Figure()

            # Add Bar chart
            fig.add_trace(
                go.Bar(
                    x=top_titles,
                    y=top_titles.index,
                    orientation='h',
                    marker=dict(color='#B53158', line=dict(color='black', width=1)),
                    hoverinfo='y+x',
                )
            )

            fig.update_layout(
                plot_bgcolor="#001220",
                paper_bgcolor="#001220",
                title='Top 10 Most Frequent Project Titles',
                xaxis_title='Frequency',
                yaxis_title='Project Titles',
                yaxis=dict(autorange="reversed"),
            )
            # Show Plotly figure
            st.plotly_chart(fig)
        except Exception as e:
            st.write(
                "An error occurred while plotting the most frequent project titles."
            )

        #################################
        # Plot Top 10 Most Frequent Words in Project Titles
        ################################
        try:
            # Initialize Plotly figure for the bar chart
            fig = go.Figure()

            # Add Bar chart
            fig.add_trace(
                go.Bar(
                    x=top_words.index,
                    y=top_words,
                    marker=dict(color='#B53158', line=dict(color='black', width=1)),
                    hoverinfo='x+y',
                )
            )
            fig.update_layout(
                plot_bgcolor="#001220",
                paper_bgcolor="#001220",
                title='Top 10 Most Frequent Words in Project Titles',
                xaxis_title='Words',
                xaxis=dict(tickangle=-45),
                yaxis_title='Frequency',
            )
            # Show Plotly figure
            st.plotly_chart(fig)
        except Exception as e:
            st.write("An error occurred while plotting the most frequent words.")

        #################################
        # Plot Deployment Type Distribution
        ################################
        try:
            # Initialize Plotly figure for the horizontal bar chart
            fig = go.Figure()

            # Add Horizontal Bar chart
            fig.add_trace(
                go.Bar(
                    x=deployment_types,
                    y=deployment_types.index,
                    orientation='h',  # Horizontal orientation
                    marker=dict(color='#B53158', line=dict(color='black', width=1)),
                    hoverinfo='x+y',
                )
            )
            fig.update_layout(
                plot_bgcolor="#001220",
                paper_bgcolor="#001220",
                title='Deployment Type Distribution',
                xaxis_title='Frequency',
                yaxis_title='Deployment Type',
                yaxis=dict(autorange="reversed"),  # Reverse the y-axis
            )
            # Show Plotly figure
            st.plotly_chart(fig)
        except Exception as e:
            st.write(
                "An error occurred while plotting the deployment type distribution."
            )

        #################################
        # Plot Cloud Provider Distribution
        ################################

        try:
            # Initialize Plotly figure for the bar chart
            fig = go.Figure()

            # Add Bar chart
            fig.add_trace(
                go.Bar(
                    x=cloud_provider_counts.index,
                    y=cloud_provider_counts,
                    marker=dict(color='#B53158', line=dict(color='black', width=1)),
                    hoverinfo='y+x',
                )
            )
            fig.update_layout(
                plot_bgcolor="#001220",
                paper_bgcolor="#001220",
                title='Cloud Provider Distribution',
                xaxis_title='Cloud Provider',
                yaxis_title='Frequency',
            )
            # Show Plotly figure
            st.plotly_chart(fig)
        except Exception as e:
            st.write(
                "An error occurred while plotting the cloud provider distribution."
            )

        ###################################################
        # Pie chart
        ###################################################

        # Initialize Plotly figure
        fig = go.Figure()
        # Add Pie chart
        fig.add_trace(
            go.Pie(
                labels=course_counts.index,
                values=course_counts,
                hole=0.8,
                rotation=90,
                marker=dict(colors=palette_colors),
                textinfo='label+percent',
                hoverinfo='label+value',
                insidetextorientation='radial',
            )
        )
        fig.update_layout(
            plot_bgcolor="#001220",
            paper_bgcolor="#001220",
            title='Distribution of Projects Across Different Courses',
        )
        # Show Plotly figure
        st.plotly_chart(fig)

        #############################
        # Stacked bar chart Projects by Year and Course
        ######################

        # Pivot the data to get counts for each 'Year' and 'Course' combination
        year_course_counts = (
            data.groupby(['Year', 'Course']).size().reset_index(name='Counts')
        )
        pivot_year_course = year_course_counts.pivot(
            index='Year', columns='Course', values='Counts'
        ).fillna(0)

        # Initialize Plotly figure
        fig = go.Figure()
        edge_color = 'black'
        gap_height = 0.2
        # Initialize the bottom_value to zero
        bottom_value = np.zeros(len(pivot_year_course))
        annotations = []

        # Plotting the stacked bar chart
        for idx, course in enumerate(course_order):
            hover_text = [
                f"{course}: {count}" for count in pivot_year_course[course].tolist()
            ]
            fig.add_trace(
                go.Bar(
                    x=pivot_year_course.index,
                    y=pivot_year_course[course],
                    base=bottom_value,
                    name=course,
                    hovertext=hover_text,
                    hoverinfo="text+x",
                    marker=dict(
                        color=palette_colors[idx], line=dict(color=edge_color, width=1)
                    ),
                )
            )
            bottom_value = [
                sum(x) for x in zip(bottom_value, pivot_year_course[course].tolist())
            ]
            bottom_value = [x + gap_height for x in bottom_value]

        # Add annotations for the sum count
        for i, x_val in enumerate(pivot_year_course.index):
            annotations.append(
                dict(
                    x=x_val,
                    y=bottom_value[i],
                    xanchor='center',
                    yanchor='bottom',
                    xshift=0,
                    yshift=4,
                    text=str(int(bottom_value[i])),
                    showarrow=False,
                    font=dict(size=14),
                )
            )

        # Update layout
        fig.update_layout(
            plot_bgcolor="#001220",
            paper_bgcolor="#001220",
            barmode='stack',
            title='Projects by Year and Course',
            xaxis_title='Year',
            yaxis_title='Counts',
            annotations=annotations,
            xaxis=dict(
                tickvals=pivot_year_course.index,
                ticktext=[str(year) for year in pivot_year_course.index],
            ),
        )

        # Show Plotly figure in Streamlit
        st.plotly_chart(fig)

        #######################
        # Stacked bar chart Distribution in Different Clouds by Course
        ##################

        # Pivot the data to get counts for each 'Cloud' and 'Course' combination
        cloud_course_counts = (
            data.groupby(['Cloud', 'Course']).size().reset_index(name='Counts')
        )
        pivot_cloud_course = cloud_course_counts.pivot(
            index='Cloud', columns='Course', values='Counts'
        ).fillna(0)

        # Initialize Plotly figure
        fig = go.Figure()
        edge_color = 'black'
        gap_height = 0.2
        bottom_value = np.zeros(len(pivot_cloud_course))
        annotations = []
        # Plotting the stacked bar chart
        for idx, course in enumerate(course_order):
            hover_text = [
                f"{course}: {count}" for count in pivot_cloud_course[course].tolist()
            ]
            fig.add_trace(
                go.Bar(
                    x=pivot_cloud_course.index,
                    y=pivot_cloud_course[course],
                    base=bottom_value,
                    name=course,
                    hovertext=hover_text,
                    hoverinfo="text+x",
                    marker=dict(
                        color=palette_colors[idx], line=dict(color=edge_color, width=1)
                    ),
                )
            )
            bottom_value = [
                sum(x) for x in zip(bottom_value, pivot_cloud_course[course].tolist())
            ]
            bottom_value = [x + gap_height for x in bottom_value]

        # Add annotations
        for i, x_val in enumerate(pivot_cloud_course.index):
            annotations.append(
                dict(
                    x=x_val,
                    y=bottom_value[i],
                    xanchor='center',
                    yanchor='bottom',
                    xshift=0,
                    yshift=4,
                    text=str(int(bottom_value[i])),
                    showarrow=False,
                    font=dict(size=14),
                )
            )
        fig.update_layout(
            plot_bgcolor="#001220",
            paper_bgcolor="#001220",
            barmode='stack',
            title='Distribution in Different Clouds by Course',
            xaxis_title='Cloud',
            yaxis_title='Counts',
            annotations=annotations,
        )

        # Show Plotly figure
        st.plotly_chart(fig)

        ##########################
        # Stacked bar chart Distribution in Different Deployment Types by Course
        ###############################

        # Pivot the data to get counts for each 'Deployment Type' and 'Course' combination
        deployment_course_counts = (
            data.groupby(['Deployment Type', 'Course'])
            .size()
            .reset_index(name='Counts')
        )
        pivot_deployment_course = deployment_course_counts.pivot(
            index='Deployment Type', columns='Course', values='Counts'
        ).fillna(0)

        # Initialize Plotly figure
        fig = go.Figure()
        edge_color = 'black'
        gap_height = 0.2
        bottom_value = np.zeros(len(pivot_deployment_course))
        annotations = []

        # Plotting the stacked bar chart
        for idx, course in enumerate(course_order):
            hover_text = [
                f"{course}: {count}"
                for count in pivot_deployment_course[course].tolist()
            ]
            fig.add_trace(
                go.Bar(
                    x=pivot_deployment_course.index,
                    y=pivot_deployment_course[course],
                    base=bottom_value,
                    name=course,
                    hovertext=hover_text,
                    hoverinfo="text+x",
                    marker=dict(
                        color=palette_colors[idx], line=dict(color=edge_color, width=1)
                    ),
                )
            )
            bottom_value = [
                sum(x)
                for x in zip(bottom_value, pivot_deployment_course[course].tolist())
            ]
            bottom_value = [x + gap_height for x in bottom_value]

        # Add annotations
        for i, x_val in enumerate(pivot_deployment_course.index):
            annotations.append(
                dict(
                    x=x_val,
                    y=bottom_value[i],
                    xanchor='center',
                    yanchor='bottom',
                    xshift=0,
                    yshift=4,
                    text=str(int(bottom_value[i])),
                    showarrow=False,
                    font=dict(size=14),
                )
            )
        fig.update_layout(
            plot_bgcolor="#001220",
            paper_bgcolor="#001220",
            barmode='stack',
            title='Deployment Types by Course',
            xaxis_title='Deployment Type',
            yaxis_title='Counts',
            annotations=annotations,
        )

        # Show Plotly figure
        st.plotly_chart(fig)

        #############################

    else:
        st.write("No data loaded.")
else:
    st.write("Please select at least one course and one year to load data.")

def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()


# Sidebar
st.sidebar.write("Help Keep This Service Running")
st.sidebar.markdown(
    "<a href='https://www.paypal.com/donate/?hosted_button_id=LR3PQYHZY4CJ4'><img src='https://www.paypalobjects.com/digitalassets/c/website/marketing/apac/C2/logos-buttons/optimize/26_Yellow_PayPal_Pill_Button.png' width='128'></a>",
    unsafe_allow_html=True,
)

share_url = "https://datatalksclub-projects.streamlit.app/"
message = "Check out this amazing Streamlit app I've been using! It offers great insights and tools. Explore it now and share your experience. #InnovativeAnalytics #Streamlit"
hashtag = "#YourHashtag"

# URL encode the message and hashtag to ensure it's web-safe
full_message = urllib.parse.quote_plus(f"{message} {hashtag}")

# Create the LinkedIn share link
linkedin_url = f"https://www.linkedin.com/sharing/share-offsite/?url={share_url}&summary={full_message}"

# Lottie Animation URL for LinkedIn Share Button
lottie_url = "https://raw.githubusercontent.com/yourusername/yourrepository/branch/yourfile.json"  # Replace with the raw URL of your Lottie file

# Load and display Lottie Animation
lottie_json = load_lottieurl(lottie_url)
if lottie_json:
    st.sidebar.markdown(f"<a href='{linkedin_url}' target='_blank'>", unsafe_allow_html=True)
    st_lottie(lottie_json, width=100, height=100, key="linkedin")
    st.sidebar.markdown("</a>", unsafe_allow_html=True)



st.sidebar.write("Connect with me")
st.sidebar.markdown(
    "<a href='https://www.linkedin.com/in/zacharenakis'><img src='https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png' width='32'></a>",
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    "<a href='https://zacharenakis.super.site'><img src='https://img.icons8.com/external-vectorslab-flat-vectorslab/53/null/external-Favorite-Website-web-and-marketing-vectorslab-flat-vectorslab.png' width='32'></a>",
    unsafe_allow_html=True,
)

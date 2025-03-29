import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt

# Load exported traces
csv_path = "./new_csv.csv"
annotated_csv_path = "./annotated_traces.csv"

# Load base data from original CSV (always prioritize latest data)
traces = pd.read_csv(csv_path)

# Add annotation columns if missing
if "feedback" not in traces.columns:
    traces["feedback"] = None
if "llm_score" not in traces.columns:
    traces["llm_score"] = None

# Merge existing annotations if annotated CSV exists
if Path(annotated_csv_path).exists():
    annotated_df = pd.read_csv(annotated_csv_path)
    # Update only annotation columns from the saved file
    traces.update(annotated_df[['feedback', 'llm_score']], overwrite=True)


# Add annotation columns if missing
if "feedback" not in traces.columns:
    traces["feedback"] = None
if "llm_score" not in traces.columns:
    traces["llm_score"] = None

def parse_json_field(json_str, field_type):
    try:
        data = json.loads(json_str)
        if field_type == "input":
            return data['messages'][-1]['content']
        elif field_type == "output":
            return data['choices'][0]['message']['content']
    except:
        return json_str

# Initialize session state for navigation and filtering
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'filtered_indices' not in st.session_state:
    st.session_state.filtered_indices = traces.index.tolist()

# Navigation functions
def go_next():
    if st.session_state.filtered_indices and st.session_state.current_index < len(st.session_state.filtered_indices) - 1:
        st.session_state.current_index += 1

def go_previous():
    if st.session_state.current_index > 0:
        st.session_state.current_index -= 1

# Title
st.title("Chatbot Feedback Tool")

# Sidebar: Reporting and Filtering
st.sidebar.header("Filter Interactions")
filter_option = st.sidebar.radio("Show:", ["All", "Annotated", "Unannotated"], index=0)

# Update filtered indices based on selection
if filter_option == "All":
    new_filtered_indices = traces.index.tolist()
elif filter_option == "Annotated":
    new_filtered_indices = traces[traces['feedback'].notna()].index.tolist()
else:
    new_filtered_indices = traces[traces['feedback'].isna()].index.tolist()

# Check if filter has changed
if new_filtered_indices != st.session_state.filtered_indices:
    st.session_state.filtered_indices = new_filtered_indices
    st.session_state.current_index = 0  # Reset to first item

# Get current original index
if st.session_state.filtered_indices:
    current_original_index = st.session_state.filtered_indices[st.session_state.current_index]
else:
    current_original_index = None

# Statistics section
st.sidebar.header("Reporting & Filtering")
show_stats = st.sidebar.checkbox("Show Statistics", value=True)

if show_stats:
    total_annotations = traces['feedback'].notna().sum()
    good_count = (traces['feedback'] == "Good").sum()
    bad_count = (traces['feedback'] == "Bad").sum()
    total = total_annotations if total_annotations > 0 else 1
    
    st.sidebar.subheader("Statistics")
    st.sidebar.write(f"Total Annotations: {total_annotations}")
    st.sidebar.write(f"Good Responses: {good_count} ({good_count/total:.2%})")
    st.sidebar.write(f"Bad Responses: {bad_count} ({bad_count/total:.2%})")

    # Pie chart
    if total_annotations > 0:
        fig, ax = plt.subplots(figsize=(6, 4))
        labels = ['Good', 'Bad']
        sizes = [good_count, bad_count]
        colors = ['#4CAF50', '#F44336']
        explode = (0.1, 0)
        ax.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
        ax.axis('equal')
        ax.set_title("Response Quality Distribution")
        st.sidebar.pyplot(fig)

# Display interaction if available
if current_original_index is not None:
    row = traces.iloc[current_original_index]
    prompt = parse_json_field(row['attributes.input.value'], "input")
    response = parse_json_field(row['attributes.output.value'], "output")

    st.subheader(f"Interaction {st.session_state.current_index + 1} of {len(st.session_state.filtered_indices)}")
    st.write(f"**Prompt**: {prompt}")
    st.write(f"**Response**: {response}")

    # LLM-as-a-Judge
    if not pd.isna(row['llm_score']):
        st.write(f"LLM Score: {row['llm_score']}")

    # Human annotation
    feedback = st.radio(
        "Is this response good?",
        ["Good", "Bad"],
        key=f"feedback_{current_original_index}",
        index=0 if row['feedback'] == "Good" else 1 if row['feedback'] == "Bad" else None,
        horizontal=True
    )
    traces.at[current_original_index, "feedback"] = feedback

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.button("Previous", on_click=go_previous, disabled=(st.session_state.current_index == 0))
    with col2:
        st.button("Next", on_click=go_next, disabled=(st.session_state.current_index == len(st.session_state.filtered_indices)-1))
    with col3:
        if st.button("Save Feedback"):
            traces.to_csv(annotated_csv_path, index=False)
            st.success("Feedback saved successfully!")
else:
    st.warning("No interactions match the current filter criteria.")


# Download Button
st.sidebar.subheader("Download Annotated Dataset")
# Filter to only annotated interactions (non-null feedback)
annotated_traces = traces[traces['feedback'].notna()]
csv_data = annotated_traces.to_csv(index=False)
st.sidebar.download_button(
    label="Download Annotated CSV",
    data=csv_data,
    file_name=f"annotated_traces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv"
)

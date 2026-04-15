import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
import os
import io
import warnings

# Silence the warnings
warnings.filterwarnings("ignore")

st.set_page_config(layout="wide", page_title="Patient Timeline")

st.title("🏥 Patient Journey Timeline (VERSION 4)")
st.markdown("Manage multiple patients using the Patient ID system below.")

# 1. Initialize empty data structure if none exists
if 'patient_data' not in st.session_state:
    st.session_state.patient_data = pd.DataFrame(columns=["start_time", "end_time", "care_level", "location", "event"])

# 2. Build the Multi-Patient Controls in the Sidebar
with st.sidebar:
    st.header("👤 Patient Selection")
    
    # User types the patient ID or name here
    patient_id = st.text_input("Enter Patient ID (e.g., 12345, Smith_J)", value="Default_Patient")
    
    # Dynamically generate the save file name based on what they typed
    SAVE_FILE = f"{patient_id}_timeline.csv"
    
    col1, col2 = st.columns(2)
    
    # Load an existing patient
    if col1.button("📂 Load Patient"):
        if os.path.exists(SAVE_FILE):
            st.session_state.patient_data = pd.read_csv(SAVE_FILE)
            st.success(f"Loaded data for {patient_id}!")
        else:
            st.error(f"No saved file found for {patient_id}.")
            
    # Clear the board for a new patient
    if col2.button("🗑️ Clear (New Patient)"):
        st.session_state.patient_data = pd.DataFrame(columns=["start_time", "end_time", "care_level", "location", "event"])
        st.rerun()

    st.divider()

    st.header("➕ Add New Event")
    with st.form("event_form", clear_on_submit=True):
        event_name = st.text_input("Event Name (e.g., Extubated)")
        
        c1, c2 = st.columns(2)
        start_date = c1.date_input("Start Date")
        start_time = c2.time_input("Start Time")
        
        c3, c4 = st.columns(2)
        end_date = c3.date_input("End Date")
        end_time = c4.time_input("End Time")
        
        care_level = st.selectbox("Care Level", ["Level 1", "Level 2", "Level 3", "Level 4", "Procedure"])
        location = st.selectbox("Location", ["Theatre/Cath lab", "PICU", "Ward 1", "Outside EMCHC"])
        
        submit = st.form_submit_button("Add to Timeline")
        
        if submit:
            start_str = f"{start_date} {start_time.strftime('%H:%M')}"
            end_str = f"{end_date} {end_time.strftime('%H:%M')}"
            
            new_event = pd.DataFrame([{
                "start_time": start_str, 
                "end_time": end_str, 
                "care_level": care_level, 
                "location": location, 
                "event": event_name
            }])
            st.session_state.patient_data = pd.concat([st.session_state.patient_data, new_event], ignore_index=True)

# 3. Create an editable table AND a Save Button
st.subheader(f"📋 Data Table for: {patient_id}")
st.session_state.patient_data = st.data_editor(
    st.session_state.patient_data, 
    num_rows="dynamic", 
    use_container_width=True
)

if st.button(f"💾 Save {patient_id} to File", type="primary"):
    if not st.session_state.patient_data.empty:
        st.session_state.patient_data.to_csv(SAVE_FILE, index=False)
        st.success(f"Data successfully saved as {SAVE_FILE}!")
    else:
        st.warning("The table is empty! Add an event before saving.")

st.divider()

# 4. The Graphing Logic
def draw_plot(df):
    df = df.copy()
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['end_time'] = pd.to_datetime(df['end_time'])
    df = df.sort_values('start_time').reset_index(drop=True)

    care_level_map = {"Level 1": 1, "Level 2": 2, "Level 3": 3, "Level 4": 4, "Procedure": 5}
    location_color_map = {"Theatre/Cath lab": "#9467bd", "PICU": "#d62728", "Ward 1": "#1f77b4", "Outside EMCHC": "#7f7f7f"}
    
    df['y_pos'] = df['care_level'].map(care_level_map)
    df['color'] = df['location'].map(location_color_map)

    fig, ax = plt.subplots(figsize=(14, 7))

    for index, row in df.iterrows():
        ax.plot([row['start_time'], row['end_time']], [row['y_pos'], row['y_pos']], 
                color=row['color'], linewidth=6, solid_capstyle='butt')
        
        if index < len(df) - 1:
            next_row = df.iloc[index + 1]
            if row['end_time'] == next_row['start_time']:
                ax.plot([row['end_time'], next_row['start_time']], [row['y_pos'], next_row['y_pos']], 
                        color='gray', linestyle='--', linewidth=1.5)

        if pd.notna(row['event']) and str(row['event']).strip() != "":
            ax.plot(row['start_time'], row['y_pos'], marker='o', markersize=9, color='black', zorder=5)
            
            lane_height = 6.2 + (index % 4) * 0.5 
            
            ax.plot([row['start_time'], row['start_time']], [row['y_pos'], lane_height], 
                    color='gray', linestyle=':', linewidth=1.5, alpha=0.6, zorder=1)

            ax.text(row['start_time'], lane_height, row['event'],
                    ha='center', va='bottom', fontsize=9, zorder=10,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9))

    ax.set_yticks(list(care_level_map.values()))
    ax.set_yticklabels(list(care_level_map.keys()), fontsize=11)
    ax.set_ylim(0.5, 8.5) 

    date_format = mdates.DateFormatter('%d %b\n%H:%M')
    ax.xaxis.set_major_formatter(date_format)
    fig.autofmt_xdate(rotation=0, ha='center')
    ax.set_xlabel('Date and Time', fontsize=12, fontweight='bold', labelpad=15)
    
    legend_patches = [mpatches.Patch(color=color, label=loc) for loc, color in location_color_map.items()]
    # THE FIX: Anchor the legend completely outside the right edge of the graph
    ax.legend(handles=legend_patches, title="Care Location", bbox_to_anchor=(1.02, 1), loc='upper left', framealpha=1)

    ax.grid(axis='x', linestyle=':', alpha=0.6)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

    ax.grid(axis='x', linestyle=':', alpha=0.6)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

    # Automatically adjust the borders so the new legend fits perfectly
    fig.tight_layout()

    return fig
    return fig

# 5. Display the Plot and PDF Export
st.subheader("📊 Visual Timeline")
if not st.session_state.patient_data.empty:
    fig = draw_plot(st.session_state.patient_data)
    st.pyplot(fig)
    
    # PDF Export feature
    buffer = io.BytesIO()
    fig.savefig(buffer, format='pdf', bbox_inches='tight')
    st.download_button(
        label="📄 Download Timeline as PDF",
        data=buffer.getvalue(),
        file_name=f"{patient_id}_timeline.pdf",
        mime="application/pdf",
    )
else:
    st.info("No data to display. Please add an event.")

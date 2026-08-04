import streamlit as st
import subprocess
import json
import os

# Ensure rclone in local bin is visible in PATH
os.environ["PATH"] = "/home/efar/.local/bin:" + os.environ.get("PATH", "")

st.set_page_config(
    page_title="Digital Library Stream",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #f8fafc;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: rgba(255,255,255,0.05);
        padding: 10px 20px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8;
        font-weight: 600;
        font-size: 16px;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #38bdf8;
    }
    .stTabs [aria-selected="true"] {
        color: #38bdf8 !important;
        border-bottom-color: #38bdf8 !important;
    }
    .card {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    .card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 20px rgba(0,0,0,0.4);
        border-color: #38bdf8;
    }
</style>
""", unsafe_allow_html=True)

st.title("🌌 Cosmic Digital Library")
st.write("Dynamic live streaming and downloading of your personal media library.")

@st.cache_data(ttl=300)
def list_library_folders():
    try:
        cmd = ["rclone", "lsjson", "stories_drive:Digital Library"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            items = json.loads(res.stdout)
            return [i["Name"] for i in items if i["IsDir"]]
    except Exception as e:
        st.error(f"Error listing library folders: {e}")
    return []

@st.cache_data(ttl=60)
def list_files_in_folder(folder_name):
    try:
        cmd = ["rclone", "lsjson", f"stories_drive:Digital Library/{folder_name}"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return json.loads(res.stdout)
    except Exception as e:
        st.error(f"Error listing files in {folder_name}: {e}")
    return []

@st.cache_data(ttl=3600)
def get_stream_link(folder_name, file_name):
    try:
        cmd = ["rclone", "link", f"stories_drive:Digital Library/{folder_name}/{file_name}"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            link = res.stdout.strip()
            # Convert drive.google.com/open?id=... to a direct streamable link
            if "drive.google.com/open?id=" in link:
                file_id = link.split("id=")[-1]
                return f"https://docs.google.com/uc?export=download&id={file_id}"
            return link
    except Exception as e:
        pass
    return None

folders = list_library_folders()

if not folders:
    st.info("Loading folders or configuring Google Drive connection...")
else:
    tabs = st.tabs([f"📁 {f.replace('_', ' ')}" for f in folders])
    
    for tab, folder in zip(tabs, folders):
        with tab:
            files = list_files_in_folder(folder)
            if not files:
                st.write("No files found in this category yet. Populating dynamically...")
            else:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.subheader("📚 Available Items")
                    selected_file = st.radio(
                        "Select an item to view / play:",
                        [f["Name"] for f in files if not f["IsDir"]],
                        key=f"radio_{folder}"
                    )
                
                with col2:
                    if selected_file:
                        st.subheader(f"✨ Viewing: {selected_file}")
                        link = get_stream_link(folder, selected_file)
                        
                        ext = os.path.splitext(selected_file)[-1].lower()
                        
                        if ext in ['.mp4', '.mkv', '.mov', '.avi']:
                            if link:
                                st.video(link)
                            else:
                                st.warning("Unable to generate direct video stream link. Try downloading below.")
                                
                        elif ext in ['.mp3', '.wav', '.ogg', '.m4a']:
                            if link:
                                st.audio(link)
                            else:
                                st.warning("Unable to generate direct audio stream link.")
                                
                        elif ext in ['.pdf', '.txt', '.html', '.epub']:
                            st.info("Readable document format. You can download it directly below.")
                            
                        # Download link
                        if link:
                            st.markdown(f'<a href="{link}" target="_blank"><button style="background-color:#38bdf8; border:none; color:white; padding:10px 20px; text-align:center; text-decoration:none; display:inline-block; font-size:16px; border-radius:8px; cursor:pointer;">📥 Download / Open in Browser</button></a>', unsafe_allow_html=True)
                        else:
                            st.error("Could not retrieve link from Google Drive.")

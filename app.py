import streamlit as st
import subprocess
import pandas as pd
import os

# Ensure rclone in local bin is visible in PATH
os.environ["PATH"] = "/home/efar/.local/bin:" + os.environ.get("PATH", "")

st.set_page_config(
    page_title="Digital Library Portal",
    page_icon="🌌",
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
    .card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 20px;
        padding: 10px 0;
    }
    .media-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 180px;
        backdrop-filter: blur(10px);
    }
    .media-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(56, 189, 248, 0.15);
        border-color: #38bdf8;
        background: rgba(255, 255, 255, 0.05);
    }
    .media-title {
        font-size: 16px;
        font-weight: 600;
        color: #f8fafc;
        margin-bottom: 8px;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    .media-meta {
        font-size: 13px;
        color: #94a3b8;
        margin-bottom: 12px;
    }
    .action-btn {
        background: #38bdf8;
        color: #0f172a !important;
        font-weight: bold;
        text-align: center;
        padding: 8px 16px;
        border-radius: 8px;
        text-decoration: none;
        display: inline-block;
        transition: background 0.2s;
        font-size: 14px;
    }
    .action-btn:hover {
        background: #0ea5e9;
    }
    .icon {
        font-size: 24px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🌌 Cosmic Digital Library")
st.write("Lightweight metadata catalog with direct high-speed Google Drive access.")

LOCAL_CSV = "/tmp/Digital_Library_Catalog.csv"

def fetch_catalog_from_drive():
    try:
        cmd = ["rclone", "copyto", "stories_drive:Digital Library/Digital_Library_Catalog.csv", LOCAL_CSV]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False

@st.cache_data(ttl=60)
def load_catalog():
    # If file doesn't exist, try fetching it
    if not os.path.exists(LOCAL_CSV):
        fetch_catalog_from_drive()
    
    if os.path.exists(LOCAL_CSV):
        try:
            return pd.read_csv(LOCAL_CSV)
        except Exception as e:
            st.error(f"Error reading catalog CSV: {e}")
    return None

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Library Tools")
    if st.button("🔄 Sync Catalog from Drive", use_container_width=True):
        st.write("Downloading fresh catalog...")
        if fetch_catalog_from_drive():
            st.cache_data.clear()
            st.success("Catalog synced successfully!")
        else:
            st.error("Failed to sync catalog. Make sure the Colab generator has completed.")

catalog = load_catalog()

if catalog is None or catalog.empty:
    st.info("Digital Library Catalog not found on Google Drive yet. Make sure your Colab generator completes and creates the catalog file.")
else:
    # Clean and formatted category mapping
    categories = sorted(catalog['Category'].unique())
    
    # Global search
    search_query = st.text_input("🔍 Search books, audio, and video files:", "").strip().lower()
    
    if search_query:
        filtered_df = catalog[catalog['Name'].str.lower().str.contains(search_query)]
        st.subheader(f"🔍 Search Results ({len(filtered_df)} matches)")
        
        # Render search result grid
        html_grid = '<div class="card-grid">'
        for idx, row in filtered_df.iterrows():
            name = row['Name']
            url = row['URL']
            size = row['Size_MB']
            cat = row['Category']
            
            icon = "📚"
            if "audio" in cat.lower():
                icon = "🎧"
            elif "video" in cat.lower():
                icon = "🎬"
                
            html_grid += f"""
            <div class="media-card">
                <div>
                    <div class="icon">{icon}</div>
                    <div class="media-title">{name}</div>
                </div>
                <div>
                    <div class="media-meta">📦 {size} MB | 📁 {cat.replace('_', ' ')}</div>
                    <a href="{url}" target="_blank" class="action-btn">🔗 View / Download</a>
                </div>
            </div>
            """
        html_grid += '</div>'
        st.markdown(html_grid, unsafe_allow_html=True)
    else:
        # Categorized Tab Layout
        tabs = st.tabs([f"📁 {c.replace('_', ' ')}" for c in categories])
        
        for tab, cat in zip(tabs, categories):
            with tab:
                cat_df = catalog[catalog['Category'] == cat]
                
                html_grid = '<div class="card-grid">'
                for idx, row in cat_df.iterrows():
                    name = row['Name']
                    url = row['URL']
                    size = row['Size_MB']
                    
                    icon = "📚"
                    if "audio" in cat.lower():
                        icon = "🎧"
                    elif "video" in cat.lower():
                        icon = "🎬"
                        
                    html_grid += f"""
                    <div class="media-card">
                        <div>
                            <div class="icon">{icon}</div>
                            <div class="media-title">{name}</div>
                        </div>
                        <div>
                            <div class="media-meta">📦 {size} MB</div>
                            <a href="{url}" target="_blank" class="action-btn">🔗 View / Download</a>
                        </div>
                    </div>
                    """
                html_grid += '</div>'
                st.markdown(html_grid, unsafe_allow_html=True)

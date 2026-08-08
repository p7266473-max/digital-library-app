import streamlit as st
import subprocess
import pandas as pd
import os
import json
import shutil

# Ensure rclone in local bin is visible in PATH
os.environ["PATH"] = "/home/efar/.local/bin:" + os.environ.get("PATH", "")

st.set_page_config(
    page_title="Cosmic Digital Library",
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
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
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
        height: 200px;
        backdrop-filter: blur(10px);
    }
    .media-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(56, 189, 248, 0.15);
        border-color: #38bdf8;
        background: rgba(255, 255, 255, 0.05);
    }
    .media-title {
        font-size: 15px;
        font-weight: 600;
        color: #f8fafc;
        margin-bottom: 8px;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        line-height: 1.4;
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
        width: 100%;
        box-sizing: border-box;
    }
    .action-btn:hover {
        background: #0ea5e9;
    }
    .icon {
        font-size: 28px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🌌 Cosmic Digital Library")
st.write("Lightweight metadata catalog with direct high-speed Google Drive access.")

LOCAL_JSON = "Digital_Library_Catalog.json"
LOCAL_EXCEL = "/tmp/Digital_Library_Catalog.xlsx"
DRIVE_TARGET_EXCEL = "stories_drive:Digital Library/Digital_Library_Catalog.xlsx"

def fetch_catalog_from_drive():
    if not shutil.which("rclone"):
        return False
    try:
        # 1. Run Rclone lsjson recursively
        cmd = ["rclone", "lsjson", "-R", "stories_drive:Digital Library"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            # Save raw JSON locally
            with open(LOCAL_JSON, "w") as f:
                f.write(res.stdout)
            
            # 2. Process to build Excel sheet for Google Drive
            items = json.loads(res.stdout)
            data = []
            for item in items:
                if item.get("IsDir"):
                    continue
                name = item.get("Name", "")
                if name.endswith("Digital_Library_Catalog.xlsx") or name.endswith("Digital_Library_Catalog.csv") or name == "00_Master_Index_and_Guide.docx":
                    continue
                    
                path = item.get("Path", "")
                parts = path.split("/")
                category = "General"
                if len(parts) >= 2:
                    category = parts[0]
                    
                file_id = item.get("ID", "")
                url = f"https://drive.google.com/open?id={file_id}" if file_id else "#"
                
                size_bytes = item.get("Size", -1)
                size_mb = size_bytes / (1024 * 1024) if size_bytes > 0 else -1
                size_mb_str = f"{size_mb:.2f}" if size_mb > 0 else "N/A"
                
                data.append({
                    "Name": name,
                    "Category": category,
                    "URL": url,
                    "Size_MB": size_mb_str
                })
            
            df = pd.DataFrame(data)
            df.to_excel(LOCAL_EXCEL, index=False)
            
            # Upload Excel to Drive
            subprocess.run(["rclone", "copyto", LOCAL_EXCEL, DRIVE_TARGET_EXCEL])
            return True
        return False
    except Exception:
        return False

category_mapping = {
    "01_Books_and_Textbooks": ("Books & Textbooks", "📚"),
    "02_Articles_and_Research_Papers": ("Articles & Journals", "🔬"),
    "02_Articles_and_Journals": ("Articles & Journals", "🔬"),
    "03_Audio_and_Podcasts": ("Audio & Podcasts", "🎧"),
    "04_Videos_and_Tutorials": ("Videos & Tutorials", "🎬"),
    "04_Video_Tutorials_and_Demos": ("Videos & Tutorials", "🎬"),
    "05_News_and_Blogs": ("News & Blogs", "📰"),
    "05_News_and_Industry_Blogs": ("News & Blogs", "📰"),
    "06_English_Language_and_Literature": ("English Learning", "🇬🇧"),
    "06_English_Language_and_Learning": ("English Learning", "🇬🇧"),
    "Scholar_Archive": ("Scholar Archive", "🏛️"),
    "General": ("General Archive", "📁")
}

@st.cache_data(ttl=60)
def load_catalog():
    if not os.path.exists(LOCAL_JSON) and shutil.which("rclone"):
        fetch_catalog_from_drive()
    
    if os.path.exists(LOCAL_JSON):
        try:
            with open(LOCAL_JSON, "r") as f:
                items = json.load(f)
            
            data = []
            for item in items:
                if item.get("IsDir"):
                    continue
                name = item.get("Name", "")
                if name.endswith("Digital_Library_Catalog.xlsx") or name.endswith("Digital_Library_Catalog.csv") or name == "00_Master_Index_and_Guide.docx":
                    continue
                    
                path = item.get("Path", "")
                parts = path.split("/")
                raw_cat = "General"
                if len(parts) >= 2:
                    raw_cat = parts[0]
                
                # Fetch clean category label and icon
                cat_info = category_mapping.get(raw_cat, ("General Archive", "📁"))
                category_label = cat_info[0]
                icon = cat_info[1]
                
                file_id = item.get("ID", "")
                url = f"https://drive.google.com/open?id={file_id}" if file_id else "#"
                
                size_bytes = item.get("Size", -1)
                size_mb = f"{size_bytes / (1024*1024):.2f}" if size_bytes > 0 else "N/A"
                
                data.append({
                    "Name": name,
                    "URL": url,
                    "Size_MB": size_mb,
                    "Category": category_label,
                    "Icon": icon
                })
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"Error reading catalog JSON: {e}")
    return None

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Library Tools")
    if shutil.which("rclone"):
        if st.button("🔄 Sync Catalog from Drive", use_container_width=True):
            st.write("Downloading fresh catalog and updating Drive Excel Sheet...")
            if fetch_catalog_from_drive():
                st.cache_data.clear()
                st.success("Catalog synced and uploaded successfully!")
            else:
                st.error("Failed to sync catalog. Please verify rclone connection.")
    else:
        st.info("ℹ️ **Cloud Mode Active**\n\nAuto-sync via Rclone is disabled in the cloud. To update library items, run the app locally, click Sync, and push the updated `Digital_Library_Catalog.json` to GitHub.")

catalog = load_catalog()

if catalog is None or catalog.empty:
    st.info("Digital Library Catalog not found. Please sync the resources from the sidebar.")
else:
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
            icon = row['Icon']
            
            # Single-line HTML string to prevent markdown code block rendering due to indentation
            html_grid += f'<div class="media-card"><div><div class="icon">{icon}</div><div class="media-title">{name}</div></div><div><div class="media-meta">📁 {cat} | 📦 {size} MB</div><a href="{url}" target="_blank" class="action-btn">🔗 View / Download</a></div></div>'
        html_grid += '</div>'
        st.markdown(html_grid, unsafe_allow_html=True)
    else:
        # Categorized Tab Layout
        # Build category tabs with matching icons
        tabs_labels = []
        for cat in categories:
            # Find the icon for this category label from the mapping
            icon = "📁"
            for k, v in category_mapping.items():
                if v[0] == cat:
                    icon = v[1]
                    break
            tabs_labels.append(f"{icon} {cat}")
            
        tabs = st.tabs(tabs_labels)
        
        for tab, cat in zip(tabs, categories):
            with tab:
                cat_df = catalog[catalog['Category'] == cat]
                
                html_grid = '<div class="card-grid">'
                for idx, row in cat_df.iterrows():
                    name = row['Name']
                    url = row['URL']
                    size = row['Size_MB']
                    icon = row['Icon']
                    
                    # Single-line HTML string to prevent markdown code block rendering due to indentation
                    html_grid += f'<div class="media-card"><div><div class="icon">{icon}</div><div class="media-title">{name}</div></div><div><div class="media-meta">📦 {size} MB</div><a href="{url}" target="_blank" class="action-btn">🔗 View / Download</a></div></div>'
                html_grid += '</div>'
                st.markdown(html_grid, unsafe_allow_html=True)

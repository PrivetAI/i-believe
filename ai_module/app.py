import streamlit as st
import logging
from ai_services.prompt_manager import PromptManager
from ui.sidebar import render_sidebar
from ui.tabs import render_script_tab, render_slides_tab, render_images_tab, render_video_tab

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="go", page_icon="🤖", layout="wide")

if 'pm' not in st.session_state:
    st.session_state.pm = PromptManager()
if 'script' not in st.session_state:
    st.session_state.script = None
if 'slides' not in st.session_state:
    st.session_state.slides = None
if 'image_prompts' not in st.session_state:
    st.session_state.image_prompts = None
if 'images' not in st.session_state:
    st.session_state.images = {}
if 'video_job_id' not in st.session_state:
    st.session_state.video_job_id = None
if 'intermediate_results' not in st.session_state:
    st.session_state.intermediate_results = {
        'script_prompt': None,
        'script_raw': None,
        'split_prompt': None,
        'split_raw': None,
        'image_prompts_request': None,
        'image_prompts_raw': None
    }
if 'available_models' not in st.session_state:
    st.session_state.available_models = {}

pm = st.session_state.pm

st.title("🤖 ")

with st.sidebar:
    config = render_sidebar(pm)

api_keys = {
    "openrouter_key": config["openrouter_key"],
    "openai_key": config["openai_key"],
    "gemini_key": config["gemini_key"],
    "fal_key": config["fal_key"],
    "imagen_key": config["imagen_key"],
    "black_forest_key": config["black_forest_key"],
    "grok_key": config["grok_key"],
    "replicate_key": config["replicate_key"]
}

tab1, tab2, tab3, tab4 = st.tabs(["1️⃣ Script", "2️⃣ Slides", "3️⃣ Images", "4️⃣ Video"])

with tab1:
    render_script_tab(pm, api_keys)

with tab2:
    render_slides_tab(pm, api_keys)

with tab3:
    render_images_tab(pm, api_keys, config["selected_style"], config["width"], config["height"])

with tab4:
    render_video_tab(pm, api_keys)
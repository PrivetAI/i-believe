import streamlit as st
import os
from ai_services.ai_provider import AIProvider
from ai_services.image_provider import ImageProvider

def render_sidebar(pm):
    """Отрисовка боковой панели с настройками"""
    
    st.header("⚙️ Configuration")
    
    # === API Keys ===
    with st.expander("🔑 API Keys", expanded=True):
        openrouter_key = st.text_input("OpenRouter API Key", type="password", value=os.getenv("OPENROUTER_API_KEY", ""))
        openai_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
        gemini_key = st.text_input("Google Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))
        
        st.divider()
        
        fal_key = st.text_input("Fal.ai API Key", type="password", value=os.getenv("FAL_KEY", ""))
        imagen_key = st.text_area("Google Imagen Service Account JSON", height=100, value=os.getenv("IMAGEN_SA_JSON", ""))
        black_forest_key = st.text_input("Black Forest Labs API Key", type="password", value=os.getenv("BFL_API_KEY", ""))
        grok_key = st.text_input("Grok (xAI) API Key", type="password", value=os.getenv("XAI_API_KEY", ""))
        replicate_key = st.text_input("Replicate API Key", type="password", value=os.getenv("REPLICATE_API_TOKEN", ""))
    
    # === AI Providers & Models ===
    with st.expander("🤖 AI Providers & Models", expanded=True):
        providers = AIProvider.get_provider_list()
        
        # Script Generation
        st.subheader("📝 Script Generation")
        script_provider_id = pm.get_provider("script")
        script_provider = st.selectbox(
            "Provider for Script",
            [p["id"] for p in providers],
            format_func=lambda x: next(p["name"] for p in providers if p["id"] == x),
            index=[p["id"] for p in providers].index(script_provider_id) if script_provider_id in [p["id"] for p in providers] else 0,
            key="script_provider"
        )
        
        if script_provider not in st.session_state.available_models:
            api_key = {"openrouter": openrouter_key, "openai": openai_key, "gemini": gemini_key}.get(script_provider)
            if api_key:
                try:
                    provider = AIProvider(script_provider, api_key)
                    st.session_state.available_models[script_provider] = provider.get_models()
                except Exception as e:
                    st.error(f"Failed to load models: {e}")
                    st.session_state.available_models[script_provider] = []
        
        script_models = st.session_state.available_models.get(script_provider, [])
        if script_models:
            current_script_model = pm.get_model("script_model")
            script_model_ids = [m["id"] for m in script_models]
            default_idx = script_model_ids.index(current_script_model) if current_script_model in script_model_ids else 0
            script_model = st.selectbox("Model for Script", script_model_ids, index=default_idx, key="script_model")
        else:
            script_model = st.text_input("Model for Script", pm.get_model("script_model") or "")
        
        if st.button("💾 Save Script Settings"):
            pm.set_provider("script", script_provider)
            pm.set_model("script_model", script_model)
            st.success("Saved!")
        
        st.divider()
        
        # Slide Splitting
        st.subheader("✂️ Slide Splitting")
        split_provider_id = pm.get_provider("split")
        split_provider = st.selectbox(
            "Provider for Split",
            [p["id"] for p in providers],
            format_func=lambda x: next(p["name"] for p in providers if p["id"] == x),
            index=[p["id"] for p in providers].index(split_provider_id) if split_provider_id in [p["id"] for p in providers] else 0,
            key="split_provider"
        )
        
        if split_provider not in st.session_state.available_models:
            api_key = {"openrouter": openrouter_key, "openai": openai_key, "gemini": gemini_key}.get(split_provider)
            if api_key:
                try:
                    provider = AIProvider(split_provider, api_key)
                    st.session_state.available_models[split_provider] = provider.get_models()
                except Exception as e:
                    st.error(f"Failed to load models: {e}")
                    st.session_state.available_models[split_provider] = []
        
        split_models = st.session_state.available_models.get(split_provider, [])
        if split_models:
            current_split_model = pm.get_model("split_model")
            split_model_ids = [m["id"] for m in split_models]
            default_idx = split_model_ids.index(current_split_model) if current_split_model in split_model_ids else 0
            split_model = st.selectbox("Model for Split", split_model_ids, index=default_idx, key="split_model")
        else:
            split_model = st.text_input("Model for Split", pm.get_model("split_model") or "")
        
        if st.button("💾 Save Split Settings"):
            pm.set_provider("split", split_provider)
            pm.set_model("split_model", split_model)
            st.success("Saved!")
        
        st.divider()
        
        # Image Prompts
        st.subheader("🎨 Image Prompts")
        image_prompts_provider_id = pm.get_provider("image_prompts")
        image_prompts_provider = st.selectbox(
            "Provider for Image Prompts",
            [p["id"] for p in providers],
            format_func=lambda x: next(p["name"] for p in providers if p["id"] == x),
            index=[p["id"] for p in providers].index(image_prompts_provider_id) if image_prompts_provider_id in [p["id"] for p in providers] else 0,
            key="image_prompts_provider"
        )
        
        if image_prompts_provider not in st.session_state.available_models:
            api_key = {"openrouter": openrouter_key, "openai": openai_key, "gemini": gemini_key}.get(image_prompts_provider)
            if api_key:
                try:
                    provider = AIProvider(image_prompts_provider, api_key)
                    st.session_state.available_models[image_prompts_provider] = provider.get_models()
                except Exception as e:
                    st.error(f"Failed to load models: {e}")
                    st.session_state.available_models[image_prompts_provider] = []
        
        image_prompts_models = st.session_state.available_models.get(image_prompts_provider, [])
        if image_prompts_models:
            current_image_prompts_model = pm.get_model("image_prompts_model")
            image_prompts_model_ids = [m["id"] for m in image_prompts_models]
            default_idx = image_prompts_model_ids.index(current_image_prompts_model) if current_image_prompts_model in image_prompts_model_ids else 0
            image_prompts_model = st.selectbox("Model for Image Prompts", image_prompts_model_ids, index=default_idx, key="image_prompts_model")
        else:
            image_prompts_model = st.text_input("Model for Image Prompts", pm.get_model("image_prompts_model") or "")
        
        if st.button("💾 Save Image Prompts Settings"):
            pm.set_provider("image_prompts", image_prompts_provider)
            pm.set_model("image_prompts_model", image_prompts_model)
            st.success("Saved!")
    
    # === Image Generation ===
    with st.expander("🖼️ Image Generation", expanded=True):
        image_providers = ImageProvider.get_provider_list()
        
        # Явно проверяем что Grok есть в списке
        print(f"Available image providers: {image_providers}")  # Debug
        
        current_image_provider = pm.get_provider("image_provider") or "imagen"
        image_provider_id = st.selectbox(
            "Image Provider",
            options=[p["id"] for p in image_providers],
            format_func=lambda x: next((p["name"] for p in image_providers if p["id"] == x), x),
            index=[p["id"] for p in image_providers].index(current_image_provider) if current_image_provider in [p["id"] for p in image_providers] else 0,
            key="image_provider_select"
        )
        
        if image_provider_id not in st.session_state.get('available_image_models', {}):
            api_key = {
                "fal": fal_key,
                "imagen": imagen_key,
                "black_forest": black_forest_key,
                "grok": grok_key,
                "replicate": replicate_key
            }.get(image_provider_id)
            
            if api_key:
                try:
                    img_provider = ImageProvider(image_provider_id, api_key)
                    if 'available_image_models' not in st.session_state:
                        st.session_state.available_image_models = {}
                    st.session_state.available_image_models[image_provider_id] = img_provider.get_models()
                except Exception as e:
                    st.error(f"Failed to load image models: {e}")
                    if 'available_image_models' not in st.session_state:
                        st.session_state.available_image_models = {}
                    st.session_state.available_image_models[image_provider_id] = []
        
        image_models = st.session_state.get('available_image_models', {}).get(image_provider_id, [])
        if image_models:
            current_image_model = pm.get_model("image_model")
            image_model_ids = [m["id"] for m in image_models]
            default_idx = image_model_ids.index(current_image_model) if current_image_model in image_model_ids else 0
            image_model = st.selectbox("Image Model", image_model_ids, format_func=lambda x: next((m["name"] for m in image_models if m["id"] == x), x), index=default_idx, key="image_model_select")
        else:
            image_model = st.text_input("Image Model", pm.get_model("image_model") or "fal-ai/flux/schnell")
        
        if st.button("💾 Save Image Settings"):
            pm.set_provider("image_provider", image_provider_id)
            pm.set_model("image_model", image_model)
            st.success("Saved!")
        
        resolution = st.selectbox("Resolution", ["9:16 (1080x1920)", "16:9 (1920x1080)"])
        width, height = (1080, 1920) if "9:16" in resolution else (1920, 1080)
    
    # === Image Styles ===
    with st.expander("🎭 Image Styles"):
        styles = pm.get_styles()
        if not styles:
            styles = ["Cinematic photography, dramatic lighting"]
        selected_style = st.selectbox("Default Style", styles)
        
        new_style = st.text_input("Add New Style")
        if st.button("➕ Add Style") and new_style:
            pm.add_style(new_style)
            st.rerun()
    
    # === Prompts ===
    with st.expander("📝 Prompts", expanded=False):
        tab1, tab2, tab3 = st.tabs(["Master", "Split", "Image Batch"])
        
        with tab1:
            master = st.text_area("Master Prompt", pm.get_prompt("master"), height=200)
            if st.button("💾 Save Master"):
                pm.set_prompt("master", master)
                st.success("Saved!")
        
        with tab2:
            split = st.text_area("Split Prompt", pm.get_prompt("split"), height=200)
            if st.button("💾 Save Split"):
                pm.set_prompt("split", split)
                st.success("Saved!")
        
        with tab3:
            image_batch = st.text_area("Image Batch Prompt", pm.get_prompt("image_batch"), height=200)
            if st.button("💾 Save Image Batch"):
                pm.set_prompt("image_batch", image_batch)
                st.success("Saved!")
    
    return {
        "openrouter_key": openrouter_key,
        "openai_key": openai_key,
        "gemini_key": gemini_key,
        "fal_key": fal_key,
        "imagen_key": imagen_key,
        "black_forest_key": black_forest_key,
        "grok_key": grok_key,
        "replicate_key": replicate_key,
        "selected_style": selected_style,
        "width": width,
        "height": height
    }
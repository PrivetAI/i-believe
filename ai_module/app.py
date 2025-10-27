import streamlit as st
import json
import os
from pathlib import Path
from ai_services.prompt_manager import PromptManager
from ai_services.openrouter_client import OpenRouterClient
from ai_services.replicate_client import ReplicateClient
from api_client import VideoGeneratorClient

st.set_page_config(page_title="go", page_icon="🤖", layout="wide")

if 'pm' not in st.session_state:
    st.session_state.pm = PromptManager()
if 'script' not in st.session_state:
    st.session_state.script = None
if 'slides' not in st.session_state:
    st.session_state.slides = None
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
        'image_prompts': {},
        'image_generation_prompts': {}
    }

pm = st.session_state.pm

st.title("🤖 ")

with st.sidebar:
    st.header("⚙️ Configuration")
    
    with st.expander("🔑 API Keys", expanded=True):
        openrouter_key = st.text_input("OpenRouter API Key", type="password", value=os.getenv("OPENROUTER_API_KEY", ""))
        replicate_key = st.text_input("Replicate API Key", type="password", value=os.getenv("REPLICATE_API_TOKEN", ""))
    
    with st.expander("🎨 Models & Settings"):
        text_model = st.text_input("Text Model", value=pm.get_model("text_model"))
        if st.button("💾 Save Text Model"):
            pm.set_model("text_model", text_model)
            st.success("Saved!")
        
        image_model = st.text_input("Image Model", value=pm.get_model("image_model"))
        if st.button("💾 Save Image Model"):
            pm.set_model("image_model", image_model)
            st.success("Saved!")
        
        resolution = st.selectbox("Resolution", ["9:16 (1080x1920)", "16:9 (1920x1080)"])
        width, height = (1080, 1920) if "9:16" in resolution else (1920, 1080)
    
    with st.expander("🎭 Image Styles"):
        styles = pm.get_styles()
        selected_style = st.selectbox("Default Style", styles)
        
        new_style = st.text_input("Add New Style")
        if st.button("➕ Add Style") and new_style:
            pm.add_style(new_style)
            st.rerun()
    
    with st.expander("📝 Prompts", expanded=False):
        tab1, tab2, tab3 = st.tabs(["Master", "Split", "Image"])
        
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
            image = st.text_area("Image Prompt", pm.get_prompt("image"), height=200)
            if st.button("💾 Save Image"):
                pm.set_prompt("image", image)
                st.success("Saved!")

tab1, tab2, tab3, tab4 = st.tabs(["1️⃣ Script", "2️⃣ Slides", "3️⃣ Images", "4️⃣ Video"])

with tab1:
    st.header("Generate Script")
    topic = st.text_input("Video Topic", placeholder="How to boost productivity with AI tools")
    
    if st.button("🎬 Generate Script", disabled=not openrouter_key or not topic):
        with st.spinner("Generating script..."):
            try:
                client = OpenRouterClient(openrouter_key)
                prompt = pm.get_prompt("master").format(topic=topic)
                
                # Сохраняем промпт
                st.session_state.intermediate_results['script_prompt'] = prompt
                
                script = client.generate(prompt, text_model, max_tokens=500)
                
                # Сохраняем raw результат
                st.session_state.intermediate_results['script_raw'] = script
                st.session_state.script = script
                
                st.success("Script generated!")
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Показываем промежуточные результаты
    if st.session_state.intermediate_results['script_prompt']:
        with st.expander("📋 Промпт для генерации скрипта", expanded=False):
            st.code(st.session_state.intermediate_results['script_prompt'], language=None)
    
    if st.session_state.intermediate_results['script_raw']:
        with st.expander("🔍 Raw результат от AI", expanded=False):
            st.code(st.session_state.intermediate_results['script_raw'], language=None)
    
    if st.session_state.script:
        st.subheader("Generated Script")
        edited_script = st.text_area("Edit if needed", st.session_state.script, height=200)
        if st.button("✅ Approve Script"):
            st.session_state.script = edited_script
            st.success("Script approved! Go to next tab.")

with tab2:
    st.header("Split into Slides")
    
    if not st.session_state.script:
        st.warning("Generate script first!")
    else:
        if st.button("✂️ Split Script", disabled=not openrouter_key):
            with st.spinner("Splitting script..."):
                try:
                    client = OpenRouterClient(openrouter_key)
                    prompt = pm.get_prompt("split").format(script=st.session_state.script)
                    
                    # Сохраняем промпт
                    st.session_state.intermediate_results['split_prompt'] = prompt
                    
                    response = client.generate(prompt, text_model, max_tokens=2000)
                    
                    # Сохраняем raw ответ
                    st.session_state.intermediate_results['split_raw'] = response
                    
                    response = response.strip()
                    if response.startswith("```json"):
                        response = response[7:]
                    if response.startswith("```"):
                        response = response[3:]
                    if response.endswith("```"):
                        response = response[:-3]
                    
                    slides = json.loads(response.strip())
                    st.session_state.slides = slides
                    st.success(f"Split into {len(slides)} slides!")
                except Exception as e:
                    st.error(f"Error: {e}")
        
        # Показываем промежуточные результаты
        if st.session_state.intermediate_results['split_prompt']:
            with st.expander("📋 Промпт для разбивки", expanded=False):
                st.code(st.session_state.intermediate_results['split_prompt'], language=None)
        
        if st.session_state.intermediate_results['split_raw']:
            with st.expander("🔍 Raw JSON от AI", expanded=True):
                st.code(st.session_state.intermediate_results['split_raw'], language="json")
        
        if st.session_state.slides:
            st.subheader(f"Slides ({len(st.session_state.slides)})")
            
            edited_slides = []
            for i, slide in enumerate(st.session_state.slides):
                col1, col2 = st.columns([1, 10])
                with col1:
                    st.write(f"**{i+1}**")
                with col2:
                    edited_text = st.text_input(f"Slide {i+1}", slide["text"], key=f"slide_{i}", label_visibility="collapsed")
                    edited_slides.append({"text": edited_text})
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Approve Slides"):
                    st.session_state.slides = edited_slides
                    st.success("Slides approved! Go to next tab.")
            with col2:
                if st.button("🔄 Regenerate"):
                    st.session_state.slides = None
                    st.rerun()

with tab3:
    st.header("Generate Images")
    
    if not st.session_state.slides:
        st.warning("Split script first!")
    else:
        if st.button("🎨 Generate All Images", disabled=not openrouter_key or not replicate_key):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                text_client = OpenRouterClient(openrouter_key)
                image_client = ReplicateClient(replicate_key)
                
                output_dir = Path("cache/ai_images")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                total = len(st.session_state.slides)
                
                for i, slide in enumerate(st.session_state.slides):
                    status_text.text(f"Generating image {i+1}/{total}...")
                    
                    img_prompt_text = pm.get_prompt("image").format(
                        script=st.session_state.script,
                        text=slide["text"],
                        style=selected_style
                    )
                    
                    # Сохраняем промпт для генерации промпта изображения
                    st.session_state.intermediate_results['image_prompts'][i] = img_prompt_text
                    
                    img_prompt = text_client.generate(img_prompt_text, text_model, max_tokens=200)
                    
                    # Сохраняем финальный промпт для изображения
                    st.session_state.intermediate_results['image_generation_prompts'][i] = img_prompt
                    
                    img_path = image_client.generate_image(
                        img_prompt,
                        image_model,
                        width=width,
                        height=height,
                        output_dir=output_dir
                    )
                    
                    st.session_state.images[i] = img_path
                    progress_bar.progress((i + 1) / total)
                
                status_text.text("✅ All images generated!")
                st.success("Images ready! Review below.")
            except Exception as e:
                st.error(f"Error: {e}")
        
        if st.session_state.images:
            st.subheader("Generated Images")
            
            for i, img_path in st.session_state.images.items():
                with st.container():
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.image(img_path, caption=f"Slide {i+1}", use_container_width=True)
                        st.caption(st.session_state.slides[i]["text"])
                    
                    with col2:
                        if i in st.session_state.intermediate_results['image_prompts']:
                            with st.expander(f"📋 Промпт для генерации промпта #{i+1}", expanded=False):
                                st.code(
                                    st.session_state.intermediate_results['image_prompts'][i],
                                    language=None
                                )
                        
                        if i in st.session_state.intermediate_results['image_generation_prompts']:
                            with st.expander(f"🎨 Финальный промпт изображения #{i+1}", expanded=False):
                                st.code(
                                    st.session_state.intermediate_results['image_generation_prompts'][i],
                                    language=None
                                )
                    
                    st.divider()
            
            if st.button("✅ Approve Images"):
                st.success("Images approved! Go to next tab.")

with tab4:
    st.header("Generate Final Video")
    
    if not st.session_state.slides or not st.session_state.images:
        st.warning("Complete previous steps first!")
    else:
        language = st.selectbox("Voice Language", ["en-US", "ru-RU", "es-ES", "de-DE", "fr-FR"])
        
        try:
            video_client = VideoGeneratorClient()
            voices = video_client.get_voices(language)
            voice = st.selectbox("Voice", [v["short_name"] for v in voices])
        except Exception as e:
            st.error(f"Cannot load voices: {e}")
            voice = None
        
        if st.button("🎬 Generate Video", disabled=not voice):
            with st.spinner("Submitting to video generator..."):
                try:
                    video_client = VideoGeneratorClient()
                    
                    slides_payload = []
                    for i, slide in enumerate(st.session_state.slides):
                        slides_payload.append({
                            "text": slide["text"],
                            "image_path": st.session_state.images[i]
                        })
                    
                    job_id = video_client.generate_video(
                        slides_payload,
                        voice,
                        resolution.split()[0]
                    )
                    
                    st.session_state.video_job_id = job_id
                    st.success(f"Job submitted: {job_id}")
                except Exception as e:
                    st.error(f"Error: {e}")
        
        if st.session_state.video_job_id:
            st.subheader("Video Generation Progress")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                video_client = VideoGeneratorClient()
                
                def update_progress(status):
                    progress = status.get("progress", 0)
                    step = status.get("current_step", "Processing...")
                    progress_bar.progress(progress)
                    status_text.text(f"{step} ({progress:.0%})")
                
                final_status = video_client.wait_for_completion(
                    st.session_state.video_job_id,
                    callback=update_progress
                )
                
                st.success("✅ Video ready!")
                
                output_path = Path("output") / f"{st.session_state.video_job_id}.mp4"
                video_client.download_video(st.session_state.video_job_id, str(output_path))
                
                st.video(str(output_path))
                
                with open(output_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download Video",
                        f,
                        file_name=f"ai_video_{st.session_state.video_job_id}.mp4",
                        mime="video/mp4"
                    )
                
            except Exception as e:
                st.error(f"Error: {e}")
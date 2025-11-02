import streamlit as st
import json
import os
from pathlib import Path
from ai_services.prompt_manager import PromptManager
from ai_services.ai_provider import AIProvider
from ai_services.replicate_client import ReplicateClient
from api_client import VideoGeneratorClient
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="go", page_icon="🤖", layout="wide")

# === Session State ===
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

# === Sidebar Configuration ===
with st.sidebar:
    st.header("⚙️ Configuration")
    
    with st.expander("🔑 API Keys", expanded=True):
        openrouter_key = st.text_input("OpenRouter API Key", type="password", value=os.getenv("OPENROUTER_API_KEY", ""))
        openai_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
        gemini_key = st.text_input("Google Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))
        replicate_key = st.text_input("Replicate API Key", type="password", value=os.getenv("REPLICATE_API_TOKEN", ""))
    
    with st.expander("🤖 AI Providers & Models", expanded=True):
        providers = AIProvider.get_provider_list()
        
        # === Script Generation ===
        st.subheader("📝 Script Generation")
        script_provider_id = pm.get_provider("script")
        script_provider = st.selectbox(
            "Provider for Script",
            [p["id"] for p in providers],
            format_func=lambda x: next(p["name"] for p in providers if p["id"] == x),
            index=[p["id"] for p in providers].index(script_provider_id) if script_provider_id in [p["id"] for p in providers] else 0,
            key="script_provider"
        )
        
        # Загрузка моделей при смене провайдера
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
            
            script_model = st.selectbox(
                "Model for Script",
                script_model_ids,
                index=default_idx,
                key="script_model"
            )
        else:
            script_model = st.text_input("Model for Script", pm.get_model("script_model") or "")
        
        if st.button("💾 Save Script Settings"):
            pm.set_provider("script", script_provider)
            pm.set_model("script_model", script_model)
            st.success("Saved!")
        
        st.divider()
        
        # === Slide Splitting ===
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
            
            split_model = st.selectbox(
                "Model for Split",
                split_model_ids,
                index=default_idx,
                key="split_model"
            )
        else:
            split_model = st.text_input("Model for Split", pm.get_model("split_model") or "")
        
        if st.button("💾 Save Split Settings"):
            pm.set_provider("split", split_provider)
            pm.set_model("split_model", split_model)
            st.success("Saved!")
        
        st.divider()
        
        # === Image Prompts ===
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
            
            image_prompts_model = st.selectbox(
                "Model for Image Prompts",
                image_prompts_model_ids,
                index=default_idx,
                key="image_prompts_model"
            )
        else:
            image_prompts_model = st.text_input("Model for Image Prompts", pm.get_model("image_prompts_model") or "")
        
        if st.button("💾 Save Image Prompts Settings"):
            pm.set_provider("image_prompts", image_prompts_provider)
            pm.set_model("image_prompts_model", image_prompts_model)
            st.success("Saved!")
    
    with st.expander("🖼️ Image Generation"):
        image_model = st.text_input("Replicate Image Model", value=pm.get_model("image_model") or "stability-ai/sdxl")
        if st.button("💾 Save Image Model"):
            pm.set_model("image_model", image_model)
            st.success("Saved!")
        
        resolution = st.selectbox("Resolution", ["9:16 (1080x1920)", "16:9 (1920x1080)"])
        width, height = (1080, 1920) if "9:16" in resolution else (1920, 1080)
    
    with st.expander("🎭 Image Styles"):
        styles = pm.get_styles()
        if not styles:
            styles = ["Cinematic photography, dramatic lighting"]
        selected_style = st.selectbox("Default Style", styles)
        
        new_style = st.text_input("Add New Style")
        if st.button("➕ Add Style") and new_style:
            pm.add_style(new_style)
            st.rerun()
    
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

# === Main Tabs ===
tab1, tab2, tab3, tab4 = st.tabs(["1️⃣ Script", "2️⃣ Slides", "3️⃣ Images", "4️⃣ Video"])

with tab1:
    st.header("Generate Script")
    topic = st.text_input("Video Topic", placeholder="How to boost productivity with AI tools")
    
    api_key_map = {"openrouter": openrouter_key, "openai": openai_key, "gemini": gemini_key}
    script_api_key = api_key_map.get(pm.get_provider("script"))
    
    if st.button("🎬 Generate Script", disabled=not script_api_key or not topic):
        with st.spinner("Generating script..."):
            try:
                logger.info(f"=== Генерация скрипта начата ===")
                logger.info(f"Тема: {topic}")
                
                provider = AIProvider(pm.get_provider("script"), script_api_key)
                model = pm.get_model("script_model")
                prompt = pm.get_prompt("master").format(topic=topic)
                
                logger.info(f"Provider: {pm.get_provider('script')}")
                logger.info(f"Модель: {model}")
                logger.info(f"Промпт ({len(prompt)} символов):\n{prompt}")
                
                st.session_state.intermediate_results['script_prompt'] = prompt
                
                script = provider.generate(prompt, model, max_tokens=32768)
                
                logger.info(f"Результат ({len(script)} символов):\n{script}")
                logger.info(f"=== Генерация скрипта завершена ===\n")
                
                st.session_state.intermediate_results['script_raw'] = script
                st.session_state.script = script
                
                st.success("Script generated!")
                st.rerun()
            except Exception as e:
                logger.error(f"Ошибка генерации скрипта: {e}", exc_info=True)
                st.error(f"Error: {e}")
    
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
        split_api_key = api_key_map.get(pm.get_provider("split"))
        
        if st.button("✂️ Split Script", disabled=not split_api_key):
            with st.spinner("Splitting script..."):
                try:
                    logger.info(f"=== Разбивка скрипта начата ===")
                    
                    provider = AIProvider(pm.get_provider("split"), split_api_key)
                    model = pm.get_model("split_model")
                    prompt = pm.get_prompt("split").format(script=st.session_state.script)
                    
                    logger.info(f"Provider: {pm.get_provider('split')}")
                    logger.info(f"Модель: {model}")
                    logger.info(f"Промпт ({len(prompt)} символов):\n{prompt}")
                    
                    st.session_state.intermediate_results['split_prompt'] = prompt
                    
                    response = provider.generate(prompt, model, max_tokens=32768)
                    
                    logger.info(f"Raw ответ ({len(response)} символов):\n{response}")
                    
                    st.session_state.intermediate_results['split_raw'] = response
                    
                    response = response.strip()
                    if response.startswith("```json"):
                        response = response[7:]
                    if response.startswith("```"):
                        response = response[3:]
                    if response.endswith("```"):
                        response = response[:-3]
                    
                    slides = json.loads(response.strip())
                    logger.info(f"Получено слайдов: {len(slides)}")
                    logger.info(f"=== Разбивка скрипта завершена ===\n")
                    
                    st.session_state.slides = slides
                    st.session_state.image_prompts = None
                    st.session_state.images = {}
                    st.success(f"Split into {len(slides)} slides!")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Ошибка разбивки скрипта: {e}", exc_info=True)
                    st.error(f"Error: {e}")
        
        if st.session_state.intermediate_results['split_prompt']:
            with st.expander("📋 Промпт для разбивки", expanded=False):
                st.code(st.session_state.intermediate_results['split_prompt'], language=None)
        
        if st.session_state.intermediate_results['split_raw']:
            with st.expander("🔍 Raw JSON от AI", expanded=False):
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
                    st.session_state.image_prompts = None
                    st.session_state.images = {}
                    st.rerun()

with tab3:
    st.header("Generate Images")
    
    if not st.session_state.slides:
        st.warning("Split script first!")
    else:
        if not st.session_state.image_prompts:
            image_prompts_api_key = api_key_map.get(pm.get_provider("image_prompts"))
            
            if st.button("📝 Generate Image Prompts", disabled=not image_prompts_api_key):
                with st.spinner("Generating image prompts..."):
                    try:
                        logger.info(f"=== Генерация промптов изображений начата ===")
                        
                        provider = AIProvider(pm.get_provider("image_prompts"), image_prompts_api_key)
                        model = pm.get_model("image_prompts_model")
                        
                        slides_text = "\n".join([f"{i+1}. {slide['text']}" for i, slide in enumerate(st.session_state.slides)])
                        
                        batch_prompt_template = pm.get_prompt("image_batch")
                        batch_prompt = batch_prompt_template.format(
                            script=st.session_state.script,
                            slides=slides_text,
                            style=selected_style
                        )

                        logger.info(f"Provider: {pm.get_provider('image_prompts')}")
                        logger.info(f"Модель: {model}")
                        logger.info(f"Промпт ({len(batch_prompt)} символов):\n{batch_prompt}")
                        
                        st.session_state.intermediate_results['image_prompts_request'] = batch_prompt
                        
                        response = provider.generate(batch_prompt, model, max_tokens=32768)
                        
                        logger.info(f"Raw ответ ({len(response)} символов):\n{response}")
                        
                        st.session_state.intermediate_results['image_prompts_raw'] = response
                        
                        response = response.strip()
                        if response.startswith("```json"):
                            response = response[7:]
                        if response.startswith("```"):
                            response = response[3:]
                        if response.endswith("```"):
                            response = response[:-3]
                        
                        prompts = json.loads(response.strip())
                        
                        if len(prompts) != len(st.session_state.slides):
                            raise ValueError(f"Expected {len(st.session_state.slides)} prompts, got {len(prompts)}")
                        
                        logger.info(f"Получено промптов: {len(prompts)}")
                        logger.info(f"=== Генерация промптов завершена ===\n")
                        
                        st.session_state.image_prompts = prompts
                        st.success(f"Generated {len(prompts)} image prompts!")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Ошибка генерации промптов: {e}", exc_info=True)
                        st.error(f"Error: {e}")
            
            if st.session_state.intermediate_results['image_prompts_request']:
                with st.expander("📋 Промпт для генерации промптов", expanded=False):
                    st.code(st.session_state.intermediate_results['image_prompts_request'], language=None)
            
            if st.session_state.intermediate_results['image_prompts_raw']:
                with st.expander("🔍 Raw JSON от AI", expanded=False):
                    st.code(st.session_state.intermediate_results['image_prompts_raw'], language="json")
        
        if st.session_state.image_prompts:
            st.subheader(f"Image Prompts ({len(st.session_state.image_prompts)})")
            
            edited_prompts = []
            for i, prompt_obj in enumerate(st.session_state.image_prompts):
                with st.container():
                    st.write(f"**Slide {i+1}:** {st.session_state.slides[i]['text']}")
                    edited_prompt = st.text_area(
                        f"Image prompt {i+1}",
                        prompt_obj["prompt"],
                        key=f"prompt_{i}",
                        height=100,
                        label_visibility="collapsed"
                    )
                    edited_prompts.append({"prompt": edited_prompt})
                    st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Approve Prompts"):
                    st.session_state.image_prompts = edited_prompts
                    st.success("Prompts approved!")
            with col2:
                if st.button("🔄 Regenerate Prompts"):
                    st.session_state.image_prompts = None
                    st.rerun()
            
            st.divider()
            
            if st.button("🎨 Generate Images from Prompts", disabled=not replicate_key):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    logger.info(f"=== Генерация изображений начата ===")
                    
                    image_client = ReplicateClient(replicate_key)
                    current_image_model = pm.get_model("image_model") or image_model
                    
                    logger.info(f"Image модель: {current_image_model}")
                    
                    output_dir = Path("cache/ai_images")
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    total = len(st.session_state.image_prompts)
                    
                    for i, prompt_obj in enumerate(st.session_state.image_prompts):
                        logger.info(f"--- Изображение {i+1}/{total} ---")
                        logger.info(f"Промпт: {prompt_obj['prompt']}")
                        
                        status_text.text(f"Generating image {i+1}/{total}...")
                        
                        img_path = image_client.generate_image(
                            prompt_obj["prompt"],
                            current_image_model,
                            width=width,
                            height=height,
                            output_dir=output_dir
                        )
                        
                        logger.info(f"Изображение сохранено: {img_path}")
                        
                        st.session_state.images[i] = img_path
                        progress_bar.progress((i + 1) / total)
                    
                    status_text.text("✅ All images generated!")
                    logger.info(f"=== Генерация изображений завершена ===\n")
                    st.success("Images ready!")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Ошибка генерации изображений: {e}", exc_info=True)
                    st.error(f"Error: {e}")
        
        if st.session_state.images:
            st.subheader("Generated Images")
            
            for i, img_path in st.session_state.images.items():
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.image(img_path, caption=f"Slide {i+1}", use_container_width=True)
                with col2:
                    st.caption(st.session_state.slides[i]["text"])
                    st.text(st.session_state.image_prompts[i]["prompt"])
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
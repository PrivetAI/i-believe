import streamlit as st
import json
from pathlib import Path
from ai_services.ai_provider import AIProvider
from ai_services.image_provider import ImageProvider
from api_client import VideoGeneratorClient
import logging

logger = logging.getLogger(__name__)

def render_script_tab(pm, api_keys):
    """Tab 1: Генерация скрипта"""
    st.header("Generate Script")
    topic = st.text_input("Video Topic", placeholder="How to boost productivity with AI tools")
    
    script_api_key = api_keys.get(pm.get_provider("script") + "_key")
    
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

def render_slides_tab(pm, api_keys):
    """Tab 2: Разбивка на слайды"""
    st.header("Split into Slides")
    
    if not st.session_state.script:
        st.warning("Generate script first!")
    else:
        split_api_key = api_keys.get(pm.get_provider("split") + "_key")
        
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

def render_images_tab(pm, api_keys, selected_style, width, height):
    """Tab 3: Генерация изображений"""
    st.header("Generate Images")
    
    if not st.session_state.slides:
        st.warning("Split script first!")
    else:
        if not st.session_state.image_prompts:
            image_prompts_api_key = api_keys.get(pm.get_provider("image_prompts") + "_key")
            
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
            
            image_provider_id = pm.get_provider("image_provider") or "imagen"
            image_api_key = {
                "fal": api_keys.get("fal_key"),
                "imagen": api_keys.get("imagen_key"),
                "black_forest": api_keys.get("black_forest_key"),
                "grok": api_keys.get("grok_key"),
                "stablehorde": api_keys.get("stablehorde_key") or "0000000000",
                "replicate": api_keys.get("replicate_key")
            }.get(image_provider_id)
            
            if st.button("🎨 Generate Images from Prompts", disabled=not image_api_key):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    logger.info(f"=== Генерация изображений начата ===")
                    
                    image_client = ImageProvider(image_provider_id, image_api_key)
                    current_image_model = pm.get_model("image_model")
                    
                    logger.info(f"Image провайдер: {image_provider_id}")
                    logger.info(f"Image модель: {current_image_model}")
                    
                    output_dir = Path("cache/ai_images")
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    total = len(st.session_state.image_prompts)
                    
                    for i, prompt_obj in enumerate(st.session_state.image_prompts):
                        logger.info(f"--- Изображение {i+1}/{total} ---")
                        logger.info(f"Промпт: {prompt_obj['prompt']}")
                        
                        status_text.text(f"Generating image {i+1}/{total}...")
                        
                        # Progress callback для Stable Horde
                        def update_horde_progress(status_info):
                            msg = status_info.get("message", "Processing...")
                            base_progress = i / total
                            item_progress = status_info.get("progress", 0) / total
                            progress_bar.progress(base_progress + item_progress)
                            status_text.text(f"Image {i+1}/{total}: {msg}")
                        
                        img_path = image_client.generate_image(
                            prompt_obj["prompt"],
                            current_image_model,
                            width=width,
                            height=height,
                            output_dir=output_dir,
                            progress_callback=update_horde_progress if image_provider_id == "stablehorde" else None
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

def render_video_tab(pm, api_keys):
    """Tab 4: Финальное видео"""
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
        
        resolution_display = st.session_state.get('resolution_display', '9:16')
        
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
                        resolution_display.split()[0]
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
"""
FFmpeg Renderer - Direct frame-by-frame rendering with VAAPI
Replaces MoviePy for maximum speed
"""
import subprocess
import numpy as np
from pathlib import Path
from typing import Generator, Tuple, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.logger import get_logger

logger = get_logger(__name__)


class FFmpegRenderer:
    """Direct FFmpeg renderer with GPU acceleration"""
    
    def __init__(self, output_path: str, resolution: Tuple[int, int], fps: int = None):
        """
        Initialize FFmpeg renderer
        
        Args:
            output_path: Output video file path
            resolution: (width, height)
            fps: Frames per second
        """
        self.output_path = output_path
        self.width, self.height = resolution
        self.fps = fps or config.DEFAULT_FPS
        self.process = None
        self.frames_written = 0
        
        logger.info(f"FFmpegRenderer: {self.width}x{self.height} @ {self.fps}fps")
    
    def detect_vaapi(self) -> bool:
        """Test if VAAPI is available"""
        try:
            result = subprocess.run(
                ['vainfo'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def start(self, audio_path: Optional[str] = None) -> subprocess.Popen:
        """
        Start FFmpeg process with pipe input
        
        Args:
            audio_path: Optional audio file to mux
            
        Returns:
            FFmpeg process
        """
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
        
        use_vaapi = self.detect_vaapi()
        
        if use_vaapi:
            logger.info("🚀 Using VAAPI GPU encoding")
            
            # VAAPI command
            cmd = [
                'ffmpeg', '-y',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{self.width}x{self.height}',
                '-pix_fmt', 'rgb24',
                '-r', str(self.fps),
                '-i', '-',  # stdin
            ]
            
            # Add audio if provided
            if audio_path and Path(audio_path).exists():
                cmd.extend(['-i', audio_path])
            
            # VAAPI encoding
            cmd.extend([
                '-init_hw_device', 'vaapi=va:/dev/dri/renderD128',
                '-filter_hw_device', 'va',
                '-vf', 'format=nv12,hwupload',
                '-c:v', 'h264_vaapi',
                '-qp', '26',
                '-c:a', 'aac' if audio_path else 'none',
                '-b:a', '192k' if audio_path else '0',
                '-movflags', '+faststart',
                self.output_path
            ])
        else:
            logger.info("💻 Using CPU encoding (libx264)")
            
            # CPU fallback
            cmd = [
                'ffmpeg', '-y',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{self.width}x{self.height}',
                '-pix_fmt', 'rgb24',
                '-r', str(self.fps),
                '-i', '-',
            ]
            
            if audio_path and Path(audio_path).exists():
                cmd.extend(['-i', audio_path])
            
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', config.MOVIEPY_PRESET,
                '-crf', str(config.CRF),
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac' if audio_path else 'none',
                '-b:a', '192k' if audio_path else '0',
                '-movflags', '+faststart',
                '-tune', 'fastdecode',
                self.output_path
            ])
        
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8  # 100MB buffer
            )
            
            # Check if process started successfully
            import time
            time.sleep(0.5)
            
            if self.process.poll() is not None:
                logger.error(f"FFmpeg process died immediately! Return code: {self.process.returncode}")
                stderr = self.process.stderr.read().decode('utf-8', errors='ignore')
                logger.error(f"FFmpeg stderr: {stderr}")
                raise RuntimeError(f"FFmpeg failed to start: {stderr}")
            
            logger.info("✓ FFmpeg process started")
            return self.process
            
        except Exception as e:
            logger.error(f"Failed to start FFmpeg: {e}", exc_info=True)
            raise
    
    def write_frame(self, frame: np.ndarray) -> bool:
        """
        Write single frame to FFmpeg
        
        Args:
            frame: RGB numpy array (height, width, 3)
            
        Returns:
            Success status
        """
        if self.process is None:
            raise RuntimeError("FFmpeg process not started")
        
        if self.process.poll() is not None:
            logger.error(f"FFmpeg process died! Return code: {self.process.returncode}")
            # Try to get stderr
            try:
                stderr = self.process.stderr.read().decode('utf-8', errors='ignore')
                logger.error(f"FFmpeg stderr: {stderr[-1000:]}")
            except:
                pass
            return False
        
        try:
            # Ensure correct shape and type
            if frame.shape != (self.height, self.width, 3):
                logger.error(f"Frame shape mismatch: {frame.shape} != {(self.height, self.width, 3)}")
                return False
            
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
            
            # Write raw RGB data
            try:
                self.process.stdin.write(frame.tobytes())
                self.frames_written += 1
                
                # Flush every 30 frames to prevent buffer buildup
                if self.frames_written % 30 == 0:
                    self.process.stdin.flush()
                
                return True
            except BrokenPipeError:
                logger.error("FFmpeg pipe broken - process may have crashed")
                # Get stderr for diagnostics
                try:
                    stderr = self.process.stderr.read().decode('utf-8', errors='ignore')
                    logger.error(f"FFmpeg stderr: {stderr[-1000:]}")
                except:
                    pass
                return False
            
        except Exception as e:
            logger.error(f"Failed to write frame {self.frames_written}: {e}", exc_info=True)
            return False
    
    def write_frames(self, frame_generator: Generator[np.ndarray, None, None]) -> int:
        """
        Write multiple frames from generator
        
        Args:
            frame_generator: Generator yielding RGB frames
            
        Returns:
            Number of frames written
        """
        count = 0
        
        try:
            for frame in frame_generator:
                if not self.write_frame(frame):
                    break
                count += 1
                
                if count % 100 == 0:
                    logger.debug(f"Written {count} frames")
            
            logger.info(f"✓ Wrote {count} frames total")
            return count
            
        except Exception as e:
            logger.error(f"Frame generation error: {e}")
            return count
    
    def finish(self) -> bool:
        """
        Finalize video and close FFmpeg
        
        Returns:
            Success status
        """
        if self.process is None:
            logger.warning("FFmpeg process already finished")
            return False
        
        try:
            logger.info("Finalizing video...")
            
            # Close stdin to signal end (only if not already closed)
            if self.process.stdin and not self.process.stdin.closed:
                try:
                    self.process.stdin.flush()
                    self.process.stdin.close()
                except Exception as e:
                    logger.warning(f"Error closing stdin: {e}")
            
            # Wait for completion
            try:
                stdout, stderr = self.process.communicate(timeout=120)
            except subprocess.TimeoutExpired:
                logger.error("FFmpeg timeout after 120s")
                self.process.kill()
                self.process.wait()
                return False
            
            if self.process.returncode != 0:
                stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
                logger.error(f"FFmpeg failed with code {self.process.returncode}")
                logger.error(f"FFmpeg stderr (last 1000 chars): {stderr_text[-1000:]}")
                return False
            
            logger.info(f"✓ Video finalized: {self.frames_written} frames")
            return True
            
        except Exception as e:
            logger.error(f"Failed to finalize: {e}", exc_info=True)
            try:
                if self.process and self.process.poll() is None:
                    self.process.kill()
                    self.process.wait()
            except:
                pass
            return False
        finally:
            self.process = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.process:
            self.finish()


def test_renderer():
    """Test FFmpeg renderer with simple gradient"""
    logger.info("Testing FFmpeg renderer...")
    
    output_path = "test_output.mp4"
    renderer = FFmpegRenderer(output_path, (1920, 1080), fps=24)
    
    def generate_test_frames():
        """Generate 48 frames (2 seconds) of gradient"""
        for i in range(48):
            frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
            frame[:, :, 0] = int((i / 48) * 255)  # Red gradient
            yield frame
    
    renderer.start()
    renderer.write_frames(generate_test_frames())
    success = renderer.finish()
    
    if success:
        logger.info(f"✓ Test successful: {output_path}")
    else:
        logger.error("✗ Test failed")
    
    return success


if __name__ == "__main__":
    test_renderer()
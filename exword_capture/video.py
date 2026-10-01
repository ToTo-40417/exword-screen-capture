"""Bounded-memory, wall-clock recording using an external FFmpeg process."""
import subprocess
import threading
import time
from .runtime import ffmpeg_executable

MAX_SCALE = 10

def integer_fit(width, height, canvas_width, canvas_height):
    if min(width, height, canvas_width, canvas_height) <= 0:
        raise ValueError("Dimensions must be positive")
    factor = min(MAX_SCALE, canvas_width // width, canvas_height // height)
    if factor < 1:
        raise ValueError("Canvas is smaller than the source")
    return factor, (canvas_width - width * factor) // 2, (canvas_height - height * factor) // 2


def frame_index(elapsed, fps):
    return max(0, int(elapsed * fps))


class Recorder:
    """Holds one latest frame, not an unbounded queue. Silence repeats that frame.

    Native RGB is piped to FFmpeg; scaling happens outside the USB/UI threads.
    If the encoder cannot keep pace, stop instead of silently shortening time.
    """
    def __init__(self, path, width, height, initial_rgb, canvas=None, fps=10, executable=None, codec=None):
        codec = codec or ("h264" if str(path).lower().endswith(".mp4") else "ffv1")
        if codec not in ("h264", "ffv1"):
            raise ValueError("Unsupported recording codec")
        executable = executable or ffmpeg_executable()
        if not executable:
            raise RuntimeError("ffmpeg_missing")
        if len(initial_rgb) != width * height * 3:
            raise ValueError("Invalid RGB frame length")
        self.width, self.height, self.fps = width, height, fps
        self.latest = initial_rgb
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.error = None
        self.frames = 0
        cw, ch = canvas or (width, height)
        factor, x, y = integer_fit(width, height, cw, ch)
        # YUV420 needs even dimensions. Add black padding, never fractional scaling.
        if codec == "h264":
            cw += cw % 2
            ch += ch % 2
        filters = f"scale={width * factor}:{height * factor}:flags=neighbor,pad={cw}:{ch}:{x}:{y}:black"
        encoding = (["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                     "-movflags", "+faststart", "-f", "mp4"] if codec == "h264" else
                    ["-c:v", "ffv1", "-level", "3", "-pix_fmt", "bgr0", "-f", "matroska"])
        command = [executable, "-hide_banner", "-loglevel", "error", "-n",
                   "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{width}x{height}",
                   "-framerate", str(fps), "-i", "pipe:0", "-vf", filters,
                   "-an", "-threads", "2", *encoding, str(path)]
        # Avoid stderr pipe deadlocks. Keep a short diagnostic file beside video.
        self.stderr = open(str(path) + ".encoder.log", "xb")
        try:
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=self.stderr,
                                            stdout=subprocess.DEVNULL,
                                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            self.stderr.close()
            raise
        self.started = time.monotonic()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def update(self, rgb):
        if len(rgb) != self.width * self.height * 3:
            raise ValueError("dimension_error")
        with self.lock:
            self.latest = rgb

    def _run(self):
        try:
            while not self.stop_event.is_set():
                deadline = self.started + self.frames / self.fps
                delay = deadline - time.monotonic()
                if delay > 0 and self.stop_event.wait(delay):
                    break
                if time.monotonic() - deadline > 2:
                    raise RuntimeError("recording_slow")
                with self.lock:
                    rgb = self.latest
                self.process.stdin.write(rgb)
                self.frames += 1
        except Exception as error:
            self.error = str(error)
        finally:
            try:
                self.process.stdin.close()
                code = self.process.wait(timeout=20)
                if code and not self.error:
                    self.error = "encoder_failed"
            except Exception as error:
                self.process.kill()
                self.process.wait()
                self.error = self.error or str(error)
            self.stderr.close()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=25)
        if self.thread.is_alive():
            self.process.kill()
            self.thread.join(timeout=5)
            self.error = self.error or "recording_timeout"

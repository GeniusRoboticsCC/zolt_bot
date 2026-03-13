import pygame
import threading
from PIL import Image

# ── CONFIG ──────────────────────────────────────────────
SCREEN_W, SCREEN_H = 800, 480
FPS = 24

GIF_MAP = {
    "neutral": "eyes/sleeping_eyes_staggered_ZZZ_20fps.gif",
    "blush":   "eyes/blushing_eyes.gif",
    "happy":   "eyes/happy.gif",
    "sad":     "eyes/sad.gif",
}
DEFAULT_EMOTION = "neutral"
# ────────────────────────────────────────────────────────


def load_gif_frames(path):
    """Load all frames from a GIF into a list of pygame surfaces."""
    gif = Image.open(path)
    frames = []
    try:
        while True:
            frame = gif.copy().convert("RGBA")
            frames.append(
                pygame.image.fromstring(frame.tobytes(), frame.size, "RGBA")
            )
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass
    return frames


class EyeDisplay:
    def __init__(self, screen):
        self.screen = screen
        self.frames = []
        self.frame_index = 0
        self.clock = pygame.time.Clock()
        self.lock = threading.Lock()
        self.set_emotion(DEFAULT_EMOTION)

    def set_emotion(self, emotion):
        path = GIF_MAP.get(emotion.lower(), GIF_MAP[DEFAULT_EMOTION])
        new_frames = load_gif_frames(path)
        with self.lock:
            self.frames = new_frames
            self.frame_index = 0
        print(f"[display] switched to → {emotion}")

    def update(self):
        with self.lock:
            if not self.frames:
                return
            frame = self.frames[self.frame_index % len(self.frames)]
            self.frame_index += 1

        self.screen.fill((0, 0, 0))
        # Centre the GIF on screen
        x = (SCREEN_W - frame.get_width()) // 2
        y = (SCREEN_H - frame.get_height()) // 2
        self.screen.blit(frame, (x, y))
        pygame.display.flip()
        self.clock.tick(FPS)


def input_loop(display):
    """Runs in a background thread — waits for typed commands."""
    print("\nType a command (blush / happy / sad / neutral) then hit Enter.")
    print("Type 'quit' to exit.\n")
    while True:
        command = input(">> ").strip().lower()
        if command == "quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            break
        elif command in GIF_MAP:
            display.set_emotion(command)
        else:
            print(f"Unknown command '{command}'. Try: {list(GIF_MAP.keys())}")


def main():
    pygame.init()

    # Use FULLSCREEN on the Pi display, or RESIZABLE for testing on a monitor
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
    # ↑ swap to pygame.RESIZABLE if you want a windowed demo on your main PC

    pygame.display.set_caption("Robot Eyes Demo")
    pygame.mouse.set_visible(False)

    display = EyeDisplay(screen)

    thread = threading.Thread(target=input_loop, args=(display,), daemon=True)
    thread.start()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Press ESC to exit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
        display.update()

    pygame.quit()


if __name__ == "__main__":
    main()
import pygame
import threading
import os
import numpy as np
from PIL import Image
import ollama

# ── RAG IMPORTS (graceful fallback if not installed) ────
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("[RAG] Libraries not installed — running without RAG.")
    print("      To enable: pip3 install sentence-transformers faiss-cpu --break-system-packages")

# ══════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════
SCREEN_W, SCREEN_H = 800, 480
FPS                = 30

GIF_MAP = {
    "sleep":    "eyes/sleeping.gif",
    "blush":    "eyes/blushing.gif",
    "happy":    "eyes/happy.gif",
    "sad":      "eyes/sad.gif",
    "thinking": "eyes/thinking.gif",
}
TRIGGER_WORDS   = set(GIF_MAP.keys())
DEFAULT_EMOTION = "sleep"
OLLAMA_MODEL    = "llama3.2:1b"

# ── RAG ─────────────────────────────────────────────────
KNOWLEDGE_FILE = "knowledge.txt"   # ← drop your .txt file here
CHUNK_SIZE     = 200               # words per chunk
CHUNK_OVERLAP  = 40                # word overlap between chunks
TOP_K          = 3                 # chunks injected per query

# ── COLOURS ─────────────────────────────────────────────
BG         = (10,  10,  15)
OVERLAY_BG = (15,  15,  25,  210)
INPUT_BG   = (35,  35,  55)
BORDER     = (60,  60,  90)
USER_CLR   = (120, 180, 255)
BOT_CLR    = (160, 230, 150)
HINT_CLR   = (80,  80,  110)
WHITE      = (220, 220, 230)
CURSOR_CLR = (180, 180, 255)
SEND_BTN   = (55,  90,  170)
TICKER_BG  = (10,  10,  20,  200)
RAG_ON_CLR = (100, 210, 120)
RAG_OFF_CLR= (180, 80,  80)

# ── SIZES ────────────────────────────────────────────────
TICKER_H  = 48
OVERLAY_H = 240
INPUT_H   = 40
MSG_PAD   = 5
# ════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════
#  RAG ENGINE
# ══════════════════════════════════════════════════════════
class RAGEngine:
    """
    Reads your knowledge.txt --> splits it into word segments --> integrate with Ollama sentence transformers
    --> Stored in FAISS index --> Upon query: retrieve most relevant chunks and inject into Ollama for context
    """

    def __init__(self):
        self.chunks  = []
        self.index   = None
        self.embedder= None
        self.enabled = False

        if not RAG_AVAILABLE:
            return
        if not os.path.exists(KNOWLEDGE_FILE):
            print(f"[RAG] '{KNOWLEDGE_FILE}' not found — RAG disabled.")
            print(f"      Create '{KNOWLEDGE_FILE}' next to demo.py to enable.")
            return

        print(f"[RAG] Reading '{KNOWLEDGE_FILE}'...")
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            text = f.read()

        self.chunks = self._chunk(text)
        print(f"[RAG] {len(self.chunks)} chunks ready.")

        print("[RAG] Loading embedding model (first run may take a moment)...")
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

        print("[RAG] Building FAISS index...")
        vecs = np.array(
            self.embedder.encode(self.chunks, show_progress_bar=False)
        ).astype("float32")
        self.index = faiss.IndexFlatL2(vecs.shape[1])
        self.index.add(vecs)

        self.enabled = True
        print("[RAG] ✓ Ready — knowledge base loaded.")

    def _chunk(self, text: str) -> list:
        words = text.split()
        chunks, i = [], 0
        while i < len(words):
            chunk = " ".join(words[i : i + CHUNK_SIZE])
            chunks.append(chunk)
            i += CHUNK_SIZE - CHUNK_OVERLAP
        return chunks

    def get_context(self, query: str) -> str:
        """Returns the most relevant chunks as a context string."""
        if not self.enabled:
            return ""
        q_vec = np.array(
            self.embedder.encode([query])
        ).astype("float32")
        _, idxs = self.index.search(q_vec, TOP_K)
        hits = [self.chunks[i] for i in idxs[0] if i < len(self.chunks)]
        return "\n\n".join(hits)

    def build_prompt(self, user_text: str) -> str:
        """Wraps user message with RAG context if available."""
        context = self.get_context(user_text)
        if not context:
            return user_text
        return (
            f"Use the following knowledge to help answer the question.\n\n"
            f"--- Knowledge ---\n{context}\n--- End ---\n\n"
            f"Question: {user_text}"
        )



#  HELPERS
def load_gif_frames(path, size):
    gif = Image.open(path)
    frames = []
    try:
        while True:
            frame = gif.copy().convert("RGBA").resize(size, Image.LANCZOS)
            frames.append(
                pygame.image.fromstring(frame.tobytes(), frame.size, "RGBA")
            )
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass
    return frames


def find_trigger(text):
    for word in text.lower().split():
        if word.strip(".,!?") in TRIGGER_WORDS:
            return word.strip(".,!?")
    return None


def wrap_text(text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]



#  EYE DISPLAY  (fullscreen GIF)
class EyeDisplay:
    def __init__(self):
        self.frames = []
        self.frame_index = 0
        self.lock = threading.Lock()
        self.current_emotion = DEFAULT_EMOTION
        self.set_emotion(DEFAULT_EMOTION)

    def set_emotion(self, emotion):
        path = GIF_MAP.get(emotion.lower(), GIF_MAP[DEFAULT_EMOTION])
        new_frames = load_gif_frames(path, (SCREEN_W, SCREEN_H))
        with self.lock:
            self.frames      = new_frames
            self.frame_index = 0
            self.current_emotion = emotion

    def draw(self, screen):
        with self.lock:
            if not self.frames:
                return
            frame = self.frames[self.frame_index % len(self.frames)]
            self.frame_index += 1
        screen.blit(frame, (0, 0))



#  RESPONSE TICKER  (always-on bottom bar)
class ResponseTicker:
    def __init__(self):
        self.font     = pygame.font.SysFont("monospace", 17)
        self.text     = ""
        self.thinking = False
        self.lock     = threading.Lock()

    def set_response(self, text):
        with self.lock:
            self.text     = text
            self.thinking = False

    def set_thinking(self, state: bool):
        with self.lock:
            self.thinking = state
            if state:
                self.text = ""

    def draw(self, screen):
        # Background bar
        bar = pygame.Surface((SCREEN_W, TICKER_H), pygame.SRCALPHA)
        bar.fill(TICKER_BG)
        screen.blit(bar, (0, SCREEN_H - TICKER_H))
        pygame.draw.line(screen, BORDER,
                         (0, SCREEN_H - TICKER_H),
                         (SCREEN_W, SCREEN_H - TICKER_H), 1)

        with self.lock:
            thinking = self.thinking
            text     = self.text

        pad_y = SCREEN_H - TICKER_H + (TICKER_H - self.font.get_height()) // 2

        if thinking:
            dots = "." * ((pygame.time.get_ticks() // 350) % 4)
            s = self.font.render(f"thinking{dots}", True, HINT_CLR)
            screen.blit(s, (12, pad_y))
            return

        if not text:
            s = self.font.render("tap face to chat", True, HINT_CLR)
            screen.blit(s, (SCREEN_W // 2 - s.get_width() // 2, pad_y))
            return

        surf   = self.font.render(text, True, BOT_CLR)
        max_w  = SCREEN_W - 24
        old_clip = screen.get_clip()
        screen.set_clip(pygame.Rect(12, SCREEN_H - TICKER_H, max_w, TICKER_H))
        x = 12 if surf.get_width() <= max_w else 12 - (surf.get_width() - max_w)
        screen.blit(surf, (x, pad_y))
        screen.set_clip(old_clip)


#  CHAT OVERLAY  (click face to open)

class ChatOverlay:
    def __init__(self, eyes: EyeDisplay, ticker: ResponseTicker, rag: RAGEngine):
        self.eyes       = eyes
        self.ticker     = ticker
        self.rag        = rag
        self.visible    = False
        self.messages   = []
        self.input_text = ""
        self.scroll     = 0
        self.thinking   = False
        self.history    = []
        self.font       = pygame.font.SysFont("monospace", 16)
        self.sfont      = pygame.font.SysFont("monospace", 13)

        panel_y = SCREEN_H - TICKER_H - OVERLAY_H
        self.panel_rect  = pygame.Rect(0, panel_y, SCREEN_W, OVERLAY_H)
        self.msg_rect    = pygame.Rect(10, panel_y + 22,
                                       SCREEN_W - 20, OVERLAY_H - INPUT_H - 36)
        self.input_rect  = pygame.Rect(10, panel_y + OVERLAY_H - INPUT_H - 6,
                                       SCREEN_W - 90, INPUT_H)
        self.send_rect   = pygame.Rect(SCREEN_W - 76,
                                       panel_y + OVERLAY_H - INPUT_H - 6,
                                       70, INPUT_H)
        self.ticker_rect = pygame.Rect(0, SCREEN_H - TICKER_H, SCREEN_W, TICKER_H)

    def toggle(self):
        self.visible = not self.visible

    def _total_h(self):
        lh = self.font.get_height() + 2
        total = 0
        for sender, text in self.messages:
            prefix = "You: " if sender == "you" else "Bot: "
            total += len(wrap_text(prefix + text, self.font,
                                   self.msg_rect.w - 12)) * lh + MSG_PAD
        return total

    def _scroll_bottom(self):
        self.scroll = max(0, self._total_h() - self.msg_rect.h)

    def add_message(self, sender, text):
        self.messages.append((sender, text))
        self._scroll_bottom()

    def send(self):
        text = self.input_text.strip()
        if not text or self.thinking:
            return
        self.input_text = ""
        self.add_message("you", text)

        trigger = find_trigger(text)
        self.eyes.set_emotion(trigger if trigger else "thinking")
        self.thinking = True
        self.ticker.set_thinking(True)

        def call_ollama():
            # Build prompt — injects RAG context if salt.txt is loaded
            prompt = self.rag.build_prompt(text)
            self.history.append({"role": "user", "content": prompt})

            try:
                resp  = ollama.chat(model=OLLAMA_MODEL, messages=self.history)
                reply = resp["message"]["content"]
                self.history.append({"role": "assistant", "content": reply})
            except Exception as e:
                reply = f"[error: {e}]"

            self.add_message("robot", reply)
            self.thinking = False
            self.ticker.set_response(reply)

            resp_trigger = find_trigger(reply)
            if resp_trigger and not trigger:
                self.eyes.set_emotion(resp_trigger)
            elif not trigger:
                self.eyes.set_emotion("sleep")

        threading.Thread(target=call_ollama, daemon=True).start()

    def handle_event(self, event):
        if not self.visible:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self.ticker_rect.collidepoint(event.pos):
                    self.toggle()
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.send()
            elif event.key == pygame.K_ESCAPE:
                self.toggle()
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.unicode and len(self.input_text) < 250:
                self.input_text += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if not self.panel_rect.collidepoint(event.pos) and \
                   not self.ticker_rect.collidepoint(event.pos):
                    self.toggle()
                elif self.send_rect.collidepoint(event.pos):
                    self.send()
            if event.button == 4:
                self.scroll = max(0, self.scroll - 20)
            if event.button == 5:
                self.scroll = min(max(0, self._total_h() - self.msg_rect.h),
                                  self.scroll + 20)

    def draw(self, screen):
        if not self.visible:
            return

        # Panel
        surf = pygame.Surface((SCREEN_W, OVERLAY_H), pygame.SRCALPHA)
        surf.fill(OVERLAY_BG)
        screen.blit(surf, (0, self.panel_rect.y))
        pygame.draw.line(screen, BORDER,
                         (0, self.panel_rect.y), (SCREEN_W, self.panel_rect.y), 1)

        # RAG status indicator (top-left of panel)
        rag_label = "RAG ON" if self.rag.enabled else "RAG OFF"
        rag_clr   = RAG_ON_CLR if self.rag.enabled else RAG_OFF_CLR
        rl = self.sfont.render(rag_label, True, rag_clr)
        screen.blit(rl, (12, self.panel_rect.y + 5))

        # Close hint (top-right of panel)
        ch = self.sfont.render("ESC / click outside to close", True, HINT_CLR)
        screen.blit(ch, (SCREEN_W - ch.get_width() - 8, self.panel_rect.y + 5))

        # Messages
        lh = self.font.get_height() + 2
        old_clip = screen.get_clip()
        screen.set_clip(self.msg_rect)
        y = self.msg_rect.y + 4 - self.scroll
        for sender, text in self.messages:
            prefix = "You: " if sender == "you" else "Bot: "
            colour = USER_CLR if sender == "you" else BOT_CLR
            for line in wrap_text(prefix + text, self.font, self.msg_rect.w - 12):
                if self.msg_rect.y <= y <= self.msg_rect.bottom:
                    screen.blit(self.font.render(line, True, colour),
                                (self.msg_rect.x + 6, y))
                y += lh
            y += MSG_PAD

        if self.thinking:
            dots = "." * ((pygame.time.get_ticks() // 350) % 4)
            t = self.sfont.render(f"thinking{dots}", True, HINT_CLR)
            screen.blit(t, (self.msg_rect.x + 6, self.msg_rect.bottom - 18))
        screen.set_clip(old_clip)

        # Input box
        pygame.draw.rect(screen, INPUT_BG, self.input_rect, border_radius=8)
        pygame.draw.rect(screen, BORDER,   self.input_rect, width=1, border_radius=8)
        ts = self.font.render(self.input_text, True, WHITE)
        tc = pygame.Rect(self.input_rect.x + 8, self.input_rect.y,
                         self.input_rect.w - 16, self.input_rect.h)
        screen.set_clip(tc)
        screen.blit(ts, (self.input_rect.x + 8,
                         self.input_rect.y + (INPUT_H - ts.get_height()) // 2))
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            cx = self.input_rect.x + 8 + ts.get_width() + 1
            cy = self.input_rect.y + 8
            pygame.draw.line(screen, CURSOR_CLR, (cx, cy), (cx, cy + INPUT_H - 16), 2)
        screen.set_clip(old_clip)

        # Send button
        pygame.draw.rect(screen, SEND_BTN, self.send_rect, border_radius=8)
        pygame.draw.rect(screen, BORDER,   self.send_rect, width=1, border_radius=8)
        sl = self.font.render("Send", True, WHITE)
        screen.blit(sl, (self.send_rect.x + (self.send_rect.w - sl.get_width()) // 2,
                         self.send_rect.y + (INPUT_H - sl.get_height()) // 2))


# ══════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
    pygame.display.set_caption("Robot")
    pygame.mouse.set_visible(True)

    # RAG boots up first — indexes txt file
    rag    = RAGEngine()
    eyes   = EyeDisplay()
    ticker = ResponseTicker()
    chat   = ChatOverlay(eyes, ticker, rag)
    clock  = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    running = False
            chat.handle_event(event)

        screen.fill(BG)
        eyes.draw(screen)
        ticker.draw(screen)
        chat.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
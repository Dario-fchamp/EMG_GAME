"""Background music from a file (pygame.mixer.music: streamed, looped). Silent if no file / no audio device."""
import os

import pygame

import config as C


def find_music_file(path=None):
    """Explicit path, or the first of C.MUSIC_FILES found in the assets folder; None if nothing found."""
    if path:
        return path if os.path.isfile(path) else None
    assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), C.ASSETS_DIR)
    for name in C.MUSIC_FILES:
        candidate = os.path.join(assets, name)
        if os.path.isfile(candidate):
            return candidate
    return None


class Music:
    def __init__(self, path=None, volume=C.MUSIC_VOLUME):
        self.ok = False
        self.volume = volume
        self.muted = False
        self.playing = False                # started (possibly paused)
        self.paused = False
        if not C.MUSIC_ENABLED:
            return
        file = find_music_file(path)
        if file is None:
            where = path or os.path.join(C.ASSETS_DIR, " / ".join(C.MUSIC_FILES))
            print(f"Music: no file found ({where}). Playing without music.")
            return
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(file)
            pygame.mixer.music.set_volume(volume)
        except pygame.error as e:
            print(f"Music: cannot play {file} ({e}). Playing without music.")
            return
        self.ok = True
        print(f"Music: {file}")

    def play(self):
        if self.ok and not self.playing:
            pygame.mixer.music.play(loops=-1)   # from the start, looping forever
            self.playing, self.paused = True, False

    def pause(self):
        if self.playing and not self.paused:
            pygame.mixer.music.pause()
            self.paused = True

    def resume(self):
        if self.paused:
            pygame.mixer.music.unpause()
            self.paused = False

    def fade_out(self):
        if self.playing:
            pygame.mixer.music.fadeout(C.MUSIC_FADEOUT_MS)
            self.playing, self.paused = False, False

    def toggle_mute(self):
        if self.ok:
            self.muted = not self.muted
            pygame.mixer.music.set_volume(0 if self.muted else self.volume)

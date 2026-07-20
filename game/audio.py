"""Lightweight procedural audio.

All sounds are synthesised at startup with numpy (no asset files to ship) and
played through ``pygame.mixer`` so several can overlap: a looping background
pad, a continuous engine hum whose pitch follows the throttle, plus one-shot
gun / crash / explosion / pickup blips.  Everything degrades gracefully -- if
pygame or an audio device is missing the whole module turns into no-ops so the
game still runs in silence.
"""

import math
import random

_RATE = 22050
_enabled = False
_sounds = {}
_engine_channel = None
_music_channel = None
_boost_channel = None
_np = None
_pygame = None

# master + per-bus gains (0..1)
MASTER = 0.9
MUSIC_VOL = 0.32
ENGINE_VOL = 0.0            # current engine channel volume (ramped)


# ---------------------------------------------------------------------------
# Synthesis helpers
# ---------------------------------------------------------------------------
def _env(n, attack=0.01, release=0.3):
    """ADSR-ish amplitude envelope over ``n`` samples."""
    np = _np
    a = max(1, int(attack * _RATE))
    r = max(1, int(release * _RATE))
    env = np.ones(n)
    a = min(a, n)
    env[:a] = np.linspace(0, 1, a)
    r = min(r, n)
    env[n - r:] = env[n - r:] * np.linspace(1, 0, r)
    return env


def _to_sound(mono, volume=1.0):
    """Turn a float array in [-1, 1] into a stereo pygame Sound."""
    np, pygame = _np, _pygame
    mono = np.clip(mono * volume, -1.0, 1.0)
    data = (mono * 32767).astype(np.int16)
    stereo = np.column_stack((data, data))
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def _noise(n):
    return _np.random.uniform(-1.0, 1.0, n)


def _lowpass(sig, k=0.15):
    """Cheap one-pole low-pass to take the harsh edge off white noise."""
    np = _np
    out = np.empty_like(sig)
    acc = 0.0
    for i in range(len(sig)):
        acc += k * (sig[i] - acc)
        out[i] = acc
    return out


# ---------------------------------------------------------------------------
# Individual sound builders
# ---------------------------------------------------------------------------
def _make_engine_loop():
    """One seamless second of a low, slightly rough motor hum."""
    np = _np
    n = _RATE
    t = np.linspace(0, 1, n, endpoint=False)
    base = 62.0                                   # fundamental (Hz)
    # a few integer harmonics keep the loop seamless
    sig = (0.6 * np.sin(2 * np.pi * base * t)
           + 0.3 * np.sin(2 * np.pi * base * 2 * t)
           + 0.15 * np.sin(2 * np.pi * base * 3 * t)
           + 0.08 * np.sin(2 * np.pi * base * 5 * t))
    # gentle wobble so it reads as a running engine, not a drone
    sig *= 1.0 + 0.12 * np.sin(2 * np.pi * 7 * t)
    sig += 0.05 * _lowpass(_noise(n), 0.25)       # combustion grit
    sig /= np.max(np.abs(sig))
    return _to_sound(sig, 0.5)


def _make_music():
    """A calm looping synth pad -- a slow four-chord progression."""
    np = _np
    bars = 4
    bar = 2.0                                      # seconds per chord
    n = int(_RATE * bar * bars)
    t = np.linspace(0, bar * bars, n, endpoint=False)
    # A minor feel: Am - F - C - G (root frequencies, low octave)
    chords = [(110.0, 130.81, 164.81),            # Am
              (87.31, 110.0, 174.61),             # F
              (130.81, 164.81, 196.0),            # C
              (98.0, 123.47, 146.83)]             # G
    out = np.zeros(n)
    seg = n // bars
    for i, chord in enumerate(chords):
        s0 = i * seg
        s1 = s0 + seg
        tt = t[s0:s1] - t[s0]
        env = np.minimum(1.0, np.minimum(tt * 3.0, (bar - tt) * 2.0))
        env = np.clip(env, 0, 1)
        voice = np.zeros(seg)
        for f in chord:
            voice += np.sin(2 * np.pi * f * tt)
            voice += 0.5 * np.sin(2 * np.pi * f * 2 * tt)   # soft octave shimmer
        out[s0:s1] += voice * env
    out /= np.max(np.abs(out))
    # a slow tremolo to breathe
    out *= 0.85 + 0.15 * np.sin(2 * np.pi * 0.25 * t)
    return _to_sound(out, 0.6)


def _make_shot(low=False):
    """A short gun 'pew': a fast downward pitch sweep plus a muzzle click.

    Kept deliberately soft and short so rapid fire layers cleanly instead of
    turning into a harsh, clipping buzz."""
    np = _np
    dur = 0.16
    n = int(_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    f0, f1 = (520, 120) if low else (880, 220)
    freq = f0 * (f1 / f0) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(freq) / _RATE
    sig = np.sin(phase) + 0.22 * np.sign(np.sin(phase))    # gentle square edge
    sig += 0.22 * _lowpass(_noise(n), 0.5) * np.exp(-t * 70)   # muzzle click
    sig *= _env(n, 0.004, dur * 0.85)
    sig /= np.max(np.abs(sig)) + 1e-6                      # normalise, no clip
    return _to_sound(sig, 0.34)


def _make_crash():
    """Metallic bang for wall / car hits."""
    np = _np
    dur = 0.42
    n = int(_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    body = _lowpass(_noise(n), 0.4)
    ring = 0.4 * np.sin(2 * np.pi * 180 * t) * np.exp(-t * 9)
    sig = (body + ring) * np.exp(-t * 7)
    return _to_sound(sig, 0.6)


def _make_explosion():
    """Deep boom for bombs / wrecks."""
    np = _np
    dur = 0.8
    n = int(_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    rumble = _lowpass(_noise(n), 0.06)
    sub = 0.6 * np.sin(2 * np.pi * 55 * t * (1 - 0.4 * t))
    sig = (rumble * 1.2 + sub) * np.exp(-t * 3.5)
    sig /= np.max(np.abs(sig)) + 1e-6
    return _to_sound(sig, 0.75)


def _make_pickup():
    """Bright two-note chime for grabbing a kit ('artifact')."""
    np = _np
    dur = 0.32
    n = int(_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    half = n // 2
    sig = np.zeros(n)
    sig[:half] += np.sin(2 * np.pi * 660 * t[:half])
    sig[half:] += np.sin(2 * np.pi * 990 * t[half:])
    sig += 0.3 * np.sin(2 * np.pi * 1320 * t)              # sparkle overtone
    sig *= _env(n, 0.005, dur * 0.7)
    return _to_sound(sig, 0.4)


def _make_shield():
    """Warm rising sweep for the shield pickup."""
    np = _np
    dur = 0.5
    n = int(_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    freq = 300 * (3.0) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(freq) / _RATE
    sig = np.sin(phase) * _env(n, 0.02, dur * 0.6)
    return _to_sound(sig, 0.4)


def _make_boost():
    """Airy whoosh loop while boosting."""
    np = _np
    n = _RATE                                       # 1s loop
    t = np.linspace(0, 1, n, endpoint=False)
    sig = _lowpass(_noise(n), 0.5)
    sig *= 0.7 + 0.3 * np.sin(2 * np.pi * 3 * t)
    sig += 0.2 * np.sin(2 * np.pi * 240 * t)
    sig /= np.max(np.abs(sig))
    return _to_sound(sig, 0.35)


def _make_thud():
    """Dull suspension thump for dropping into a pothole."""
    np = _np
    dur = 0.28
    n = int(_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    # low body resonance sliding down, plus a short gritty scuff
    body = np.sin(2 * np.pi * 95 * (1 - 0.45 * t) * t)
    body += 0.5 * np.sin(2 * np.pi * 58 * (1 - 0.3 * t) * t)
    scuff = 0.35 * _lowpass(_noise(n), 0.18) * np.exp(-t * 26)
    sig = (body * np.exp(-t * 13) + scuff)
    sig /= np.max(np.abs(sig)) + 1e-6
    return _to_sound(sig, 0.7)


def _make_beep(freq=440, dur=0.18):
    np = _np
    n = int(_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    sig = np.sin(2 * np.pi * freq * t) * _env(n, 0.005, dur * 0.5)
    return _to_sound(sig, 0.4)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def init():
    """Initialise the mixer and synthesise every sound. Safe to call once."""
    global _enabled, _np, _pygame, _engine_channel, _music_channel, _boost_channel
    if _enabled:
        return
    try:
        import numpy as np
        import pygame
        pygame.mixer.pre_init(_RATE, -16, 2, 512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(32)
        # Reserve 0..2 for the music / engine / boost loops. Without this,
        # play()'s find_channel(force=True) steals the LONGEST-playing channel
        # -- which is always one of those loops -- so every gunshot chopped the
        # music and engine out. Reserved channels are never handed out.
        pygame.mixer.set_reserved(3)
    except Exception:
        _enabled = False
        return
    _np, _pygame = np, pygame
    try:
        _sounds['engine'] = _make_engine_loop()
        _sounds['music'] = _make_music()
        _sounds['shot'] = _make_shot(False)
        _sounds['eshot'] = _make_shot(True)
        _sounds['crash'] = _make_crash()
        _sounds['explosion'] = _make_explosion()
        _sounds['pickup'] = _make_pickup()
        _sounds['shield'] = _make_shield()
        _sounds['boost'] = _make_boost()
        _sounds['thud'] = _make_thud()
        _sounds['beep'] = _make_beep(523)
        _sounds['go'] = _make_beep(880, 0.4)
        _engine_channel = pygame.mixer.Channel(0)
        _music_channel = pygame.mixer.Channel(1)
        _boost_channel = pygame.mixer.Channel(2)
        _enabled = True
    except Exception:
        _enabled = False


def play(name, volume=1.0):
    """Fire a one-shot sound on any free channel."""
    if not _enabled:
        return
    snd = _sounds.get(name)
    if snd is None:
        return
    ch = _pygame.mixer.find_channel(True)
    if ch is not None:
        ch.set_volume(min(1.0, volume * MASTER))
        ch.play(snd)


def start_music():
    if not _enabled:
        return
    _music_channel.set_volume(MUSIC_VOL * MASTER)
    if not _music_channel.get_busy():
        _music_channel.play(_sounds['music'], loops=-1)


def stop_music():
    if not _enabled:
        return
    _music_channel.stop()


def start_engine():
    """Begin the looping engine hum (starts near-silent, ramp with throttle)."""
    if not _enabled:
        return
    if not _engine_channel.get_busy():
        _engine_channel.set_volume(0.0)
        _engine_channel.play(_sounds['engine'], loops=-1)


def stop_engine():
    if not _enabled:
        return
    _engine_channel.stop()
    _boost_channel.stop()


def set_engine(throttle):
    """Set engine loudness from a 0..1 throttle proxy (called each frame)."""
    if not _enabled:
        return
    vol = (0.18 + 0.5 * max(0.0, min(1.0, throttle))) * MASTER
    _engine_channel.set_volume(vol)


def set_boost(active):
    """Toggle the looping boost whoosh."""
    if not _enabled:
        return
    if active:
        if not _boost_channel.get_busy():
            _boost_channel.set_volume(0.5 * MASTER)
            _boost_channel.play(_sounds['boost'], loops=-1)
    else:
        _boost_channel.stop()


def stop_all():
    if not _enabled:
        return
    _pygame.mixer.stop()

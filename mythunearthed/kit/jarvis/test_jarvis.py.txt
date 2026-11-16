"""Тестове без микрофон: синтетично аудио, „Джарвис … край“ и команди."""
import numpy as np

from jarvis import BLOCK, SAMPLERATE, ClapDetector, CommandAssembler, load_config, match_command

rng = np.random.default_rng(0)
CFG = load_config()


def make_audio(events, seconds=3.0):
    """events: [(начало_сек, продължителност_сек, сила)]"""
    audio = rng.normal(0, 0.005, int(seconds * SAMPLERATE)).astype(np.float32)
    for start, length, amp in events:
        i, n = int(start * SAMPLERATE), int(length * SAMPLERATE)
        env = np.exp(-np.linspace(0, 6, n))
        audio[i:i + n] += (rng.normal(0, 1, n) * amp * env).astype(np.float32)
    return audio


def count_triggers(audio):
    det, hits = ClapDetector(), 0
    for k in range(0, len(audio) - BLOCK, BLOCK):
        hits += det.process(audio[k:k + BLOCK], (k + BLOCK) / SAMPLERATE)
    return hits


# --- пляскане
def test_double_clap_triggers():
    assert count_triggers(make_audio([(1.0, 0.05, 0.6), (1.35, 0.05, 0.6)])) == 1


def test_single_clap_does_not():
    assert count_triggers(make_audio([(1.0, 0.05, 0.6)])) == 0


def test_claps_too_far_apart():
    assert count_triggers(make_audio([(0.5, 0.05, 0.6), (2.0, 0.05, 0.6)])) == 0


def test_long_sound_is_not_clap():
    audio = make_audio([])
    audio[16000:48000] += (0.3 * np.sin(np.arange(32000) / 5)).astype(np.float32)
    assert count_triggers(audio) == 0


def test_fast_speech_bursts_are_not_claps():
    # кратки срички почти без пауза между тях (като говор)
    bursts = [(0.5 + i * 0.13, 0.08, 0.4) for i in range(10)]
    assert count_triggers(make_audio(bursts)) == 0


# --- „Джарвис … край“
def asm():
    return CommandAssembler(CFG["wake_words"], CFG["end_words"], timeout=20)


def test_one_phrase_command():
    a = asm()
    assert a.feed("Джарвис пусни в youtube лофи музика край", 0) == ("command", "пусни в youtube лофи музика")


def test_command_in_parts():
    a = asm()
    assert a.feed("джарвис", 0) == ("listening", None)
    assert a.feed("търси рецепта за мусака", 2) == ("listening", None)
    assert a.feed("край", 4) == ("command", "търси рецепта за мусака")


def test_ignored_without_name():
    a = asm()
    assert a.feed("пусни музика край", 0) == (None, None)
    assert a.feed("това е крайно време", 1) == (None, None)


def test_kraino_is_not_end_word():
    a = asm()
    assert a.feed("джарвис търси крайпътни заведения", 0) == ("listening", None)
    assert a.feed("край", 1) == ("command", "търси крайпътни заведения")


def test_timeout_cancels():
    a = asm()
    a.feed("джарвис отвори пощата", 0)
    assert a.timed_out(25)
    assert a.feed("край", 26) == (None, None)


def test_english_spelling_of_name():
    assert asm().feed("Jarvis колко е часът край", 0) == ("command", "колко е часът")


# --- команди
def test_commands():
    cmds = CFG["commands"]
    cmd, rest = match_command("търси рецепта за мусака", cmds)
    assert "търси" in cmd["phrases"] and rest == "рецепта за мусака"
    cmd, rest = match_command("пусни в youtube лофи музика", cmds)
    assert rest == "лофи музика"
    assert match_command("изключи компютъра", cmds)[0]["actions"][0]["target"] == "shutdown"
    assert match_command("заключи компютъра", cmds)[0]["actions"][0]["target"] == "lock"
    assert match_command("кажи ми виц за котки", cmds)[0] is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)

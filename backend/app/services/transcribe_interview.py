#!/usr/bin/env python3
"""Interview-Aufnahme (OBS .mkv) mit Nemotron-3.5-Transcribe transkribieren -> Markdown im Dialogformat.

OBS-Spuren: 1 = Mix, 2 = Ich, 3 = Interviewpartner.

Modi:
  mix     Mix-Spur mit Sprecher-Tags <spk:N> + Wort-Zeitstempeln. Sprecher-Tags werden automatisch
          "Ich"/"Partner" zugeordnet, indem die Pegel der Einzelspuren 2/3 im Zeitfenster jedes Wortes
          verglichen werden (Fallback: Sprecher 0/1/...).
  tracks  Spur 2 und 3 getrennt transkribieren (ohne Diarization), Wörter per Zeitstempel zusammenführen.

Aufnahmen > 55 min werden in überlappende Blöcke geteilt; Wörter in der Überlappung werden in der Mitte
der Überlappung zwischen den Blöcken aufgeteilt.

Nur Python-Standardbibliothek + ffmpeg/ffprobe nötig.

Beispiele:
  ./transcribe_interview.py aufnahme.mkv
  ./transcribe_interview.py aufnahme.mkv --mode tracks --terms "SestigSystems, DigiKey, Nexar"
  ./transcribe_interview.py aufnahme.mkv --terms-file begriffe.txt -o interview.md --partner "Frau Müller"
"""

# ---------------------------------------------------------------- Konfiguration
SERVER_URL = "http://192.168.101.95:8001/v1"
MODEL_NAME = "nvidia/NVIDIA-Nemotron-3.5-Transcribe-30B-A4B-NVFP4"
API_KEY = "EMPTY"

TRACK_MIX, TRACK_ME, TRACK_PARTNER = 1, 2, 3   # 1-basierte Audiospur-Nummern in der .mkv
NAME_ME, NAME_PARTNER = "Ich", "Partner"

SPLIT_THRESHOLD_S = 55 * 60   # ab dieser Länge wird geteilt
CHUNK_S = 50 * 60             # Blocklänge
OVERLAP_S = 2 * 60            # Überlappung zwischen Blöcken
TURN_GAP_S = 3.0              # neuer Absatz bei Pause > x s (auch ohne Sprecherwechsel)
MAX_TURN_S = 90.0             # lange Monologe nach Satzende umbrechen
REQUEST_TIMEOUT_S = 3600
# Schutz gegen Wiederholungsschleifen des Modells: Token-Deckel pro Block und Plausibilitätsprüfung.
# Schlägt ein Block fehl (Deckel erreicht, Ausrichtung fehlgeschlagen, unplausibel viele Wörter),
# wird er halbiert und neu angefragt, bis MIN_SPLIT_S erreicht ist.
TOKENS_PER_S = 10             # Karte: dichte 1-h-Aufnahme ~20k Tokens (~6/s)
MAX_WORDS_PER_S = 4.5         # normale Sprache ~2-3 Wörter/s
MIN_SPLIT_S = 4 * 60
SPLIT_OVERLAP_S = 30
# ------------------------------------------------------------------------------

import argparse
import array
import base64
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

SR = 16000
SPK_TAG_RE = re.compile(r"<spk:(\d+)>")
ANY_TAG_RE = re.compile(r"<[^<>\s]{1,40}>")

PROMPT_PLAIN = ("Transcribe this audio with punctuation and capitalization. "
                "Include all spoken words and verbal fillers. Write numbers in their standard written form.")
PROMPT_SPK = PROMPT_PLAIN + " Put speaker tags <spk:0> <spk:1> <spk:2> <spk:3> on the transcription."


# ------------------------------------------------------------------ Audio
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"Fehler bei: {' '.join(cmd)}\n{r.stderr[-2000:]}")
    return r.stdout


def audio_track_count(src: Path) -> int:
    out = run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
               "-of", "csv=p=0", str(src)])
    return len([l for l in out.splitlines() if l.strip()])


def extract_wav(src: Path, track: int, dst: Path, start: float | None = None, dur: float | None = None):
    """Audiospur (1-basiert) -> 16 kHz mono 16-bit WAV."""
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", str(src)]
    if dur is not None:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-map", f"0:a:{track - 1}", "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(dst)]
    run(cmd)


def wav_duration(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def load_pcm(path: Path) -> array.array:
    with wave.open(str(path)) as w:
        a = array.array("h")
        a.frombytes(w.readframes(w.getnframes()))
    if sys.byteorder == "big":
        a.byteswap()
    return a


def cut_wav(src: Path, dst: Path, start: float, dur: float):
    with wave.open(str(src)) as w:
        w.setpos(min(int(start * SR), w.getnframes()))
        frames = w.readframes(int(dur * SR))
        params = w.getparams()
    with wave.open(str(dst), "wb") as o:
        o.setparams(params)
        o.writeframes(frames)


def energy(pcm: array.array, t0: float, t1: float) -> float:
    i0, i1 = max(0, int(t0 * SR)), min(len(pcm), int(t1 * SR))
    if i1 <= i0:
        return 0.0
    step = max(1, (i1 - i0) // 4000)   # Stichprobe reicht für den Pegelvergleich
    s = sum(pcm[i] * pcm[i] for i in range(i0, i1, step))
    return math.sqrt(s / len(range(i0, i1, step)))


# ------------------------------------------------------------------ Server
def transcribe(wav_path: Path, prompt: str, max_tokens: int, timestamps: bool = True) -> dict:
    audio_b64 = base64.b64encode(wav_path.read_bytes()).decode()
    body = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "audio_url", "audio_url": {"url": f"data:audio/wav;base64,{audio_b64}"}},
        ]}],
        "temperature": 0,
        "top_p": 1.0,
        "seed": 0,
        "stream": False,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
        "skip_special_tokens": False,
        "spaces_between_special_tokens": False,
    }
    if timestamps:
        body["mm_processor_kwargs"] = {"capture_ctc_timestamps": True}
    req = urllib.request.Request(f"{SERVER_URL}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Server-Fehler {e.code}: {e.read().decode(errors='replace')[:2000]}")


def response_words(resp: dict, offset: float) -> tuple[list[dict], str, str | None]:
    """Wörter (absolute Zeiten) aus ctc_timestamps, Rohtext, Fehlergrund (None = ok)."""
    text = resp["choices"][0]["message"].get("content") or ""
    ts = resp.get("ctc_timestamps") or {}
    if not ts or ts.get("error") is not None:
        return [], text, (ts.get("error") if ts else "keine ctc_timestamps")
    words = []
    for w in ts.get("words", []):
        t = ANY_TAG_RE.sub("", str(w.get("word", ""))).strip()
        if not t:
            continue
        spk = w.get("speaker")
        m = SPK_TAG_RE.search(str(spk)) if spk is not None else None
        words.append({"word": t, "start": float(w["start"]) + offset, "end": float(w["end"]) + offset,
                      "spk": int(m.group(1)) if m else (int(spk) if str(spk).isdigit() else spk)})
    return words, text, None


def fallback_words(text: str, start: float, dur: float, default_spk) -> list[dict]:
    """Ohne Zeitstempel: Wörter linear über die Blockdauer verteilen (Zeiten nur ungefähr)."""
    toks, spk = [], default_spk
    for part in re.split(r"(<spk:\d+>)", text):
        m = SPK_TAG_RE.fullmatch(part)
        if m:
            spk = int(m.group(1))
        else:
            toks += [(t, spk) for t in ANY_TAG_RE.sub("", part).split()]
    n = max(1, len(toks))
    return [{"word": t, "start": start + dur * i / n, "end": start + dur * (i + 1) / n, "spk": sp, "approx": True}
            for i, (t, sp) in enumerate(toks)]


# ------------------------------------------------------------------ Blöcke
def plan_chunks(duration: float) -> list[tuple[float, float, float, float]]:
    """(start, dauer, keep_from, keep_to) – Wörter mit start in [keep_from, keep_to) werden behalten."""
    if duration <= SPLIT_THRESHOLD_S:
        return [(0.0, duration, 0.0, math.inf)]
    starts, s = [], 0.0
    while True:
        starts.append(s)
        if s + CHUNK_S >= duration:
            break
        s += CHUNK_S - OVERLAP_S
    chunks = []
    for i, st in enumerate(starts):
        dur = min(CHUNK_S, duration - st)
        keep_from = 0.0 if i == 0 else st + OVERLAP_S / 2
        keep_to = math.inf if i == len(starts) - 1 else starts[i + 1] + OVERLAP_S / 2
        chunks.append((st, dur, keep_from, keep_to))
    return chunks


def transcribe_span(wav: Path, st: float, dur: float, kf: float, kt: float, prompt: str, tmp: Path,
                    label: str, default_spk, depth: int = 0) -> list[list[dict]]:
    """Transkribiert [st, st+dur) und liefert Einheiten (Wortlisten mit absoluten Zeiten, gefiltert auf
    [kf, kt)). Sprecher-Tag-Nummern gelten nur innerhalb einer Einheit."""
    part = tmp / f"{wav.stem}_{st:.0f}_{dur:.0f}.wav"
    cut_wav(wav, part, st, dur)
    ind = "  " * (depth + 1)
    print(f"{ind}{label}: {fmt_ts(st)}–{fmt_ts(st + dur)} ...", file=sys.stderr)
    t0 = time.time()
    resp = transcribe(part, prompt, max_tokens=int(dur * TOKENS_PER_S) + 512)
    words, text, err = response_words(resp, st)
    finish = resp["choices"][0].get("finish_reason")
    if finish == "length":
        err = "Token-Deckel erreicht (Wiederholungsschleife?)"
    elif not err and len(words) / max(dur, 1) > MAX_WORDS_PER_S:
        err = f"unplausibel viele Wörter ({len(words) / dur:.1f}/s)"
    print(f"{ind}  {time.time() - t0:.0f} s, {len(words)} Wörter" + (f" – PROBLEM: {err}" if err else ""),
          file=sys.stderr)
    part.unlink(missing_ok=True)
    if err and dur > MIN_SPLIT_S:
        mid = st + dur / 2
        print(f"{ind}  -> teile Block in zwei Hälften", file=sys.stderr)
        a = transcribe_span(wav, st, dur / 2 + SPLIT_OVERLAP_S / 2, max(kf, st), min(kt, mid),
                            prompt, tmp, label, default_spk, depth + 1)
        b = transcribe_span(wav, mid - SPLIT_OVERLAP_S / 2, dur / 2 + SPLIT_OVERLAP_S / 2, max(kf, mid), kt,
                            prompt, tmp, label, default_spk, depth + 1)
        return a + b
    if err:
        print(f"{ind}  -> nutze Text ohne Wort-Zeitstempel (Zeiten ungefähr, mit ~ markiert)", file=sys.stderr)
        if finish == "length":
            text = collapse_repeats(text)
        words = fallback_words(text, st, dur, default_spk)
    return [[w for w in words if kf <= w["start"] < kt]]


def collapse_repeats(text: str, n: int = 8) -> str:
    """Entfernt eine am Ende in Schleife wiederholte Wortfolge (grob)."""
    toks = text.split()
    for size in range(n, 60):
        if len(toks) < 3 * size:
            break
        tail = toks[-size:]
        i = len(toks) - size
        while i - size >= 0 and toks[i - size:i] == tail:
            i -= size
        if len(toks) - i >= 3 * size:
            return " ".join(toks[:i + size]) + " [...]"
    return text


def run_chunks(wav: Path, prompt: str, tmp: Path, label: str, default_spk=0) -> list[list[dict]]:
    """Transkribiert eine WAV ggf. blockweise. Liefert Einheiten (Wortlisten mit absoluten Zeiten)."""
    units = []
    for st, dur, kf, kt in plan_chunks(wav_duration(wav)):
        units += transcribe_span(wav, st, dur, kf, kt, prompt, tmp, label, default_spk)
    return units


# ------------------------------------------------------------------ Ausgabe
def fmt_ts(s: float) -> str:
    s = int(s)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def build_turns(words: list[dict]) -> list[dict]:
    turns = []
    for w in sorted(words, key=lambda w: w["start"]):
        cur = turns[-1] if turns else None
        new = (cur is None or w["name"] != cur["name"] or w["start"] - cur["end"] > TURN_GAP_S
               or (w["start"] - cur["start"] > MAX_TURN_S and cur["words"][-1].endswith((".", "?", "!"))))
        if new:
            turns.append({"name": w["name"], "start": w["start"], "end": w["end"], "words": [w["word"]],
                          "approx": w.get("approx", False)})
        else:
            cur["words"].append(w["word"])
            cur["end"] = max(cur["end"], w["end"])
    return turns


def write_markdown(dst: Path, src: Path, mode: str, terms: list[str], turns: list[dict], duration: float):
    lines = [f"# Transkript: {src.name}", "",
             f"- Dauer: {fmt_ts(duration)}",
             f"- Modus: {mode}",
             f"- Modell: {MODEL_NAME}",
             f"- Erstellt: {time.strftime('%Y-%m-%d %H:%M')}"]
    if terms:
        lines.append(f"- Kontextbegriffe: {', '.join(terms)}")
    lines += ["", "---", ""]
    for t in turns:
        text = re.sub(r"\s+([,.;:!?])", r"\1", " ".join(t["words"]))
        lines += [f"**[{'~' if t['approx'] else ''}{fmt_ts(t['start'])}] {t['name']}:** {text}", ""]
    dst.write_text("\n".join(lines), encoding="utf-8")


# ------------------------------------------------------------------ Modi
def mode_mix(src, tmp, prompt, has_tracks, names):
    mix = tmp / "mix.wav"
    extract_wav(src, TRACK_MIX, mix)
    duration = wav_duration(mix)
    pcm_me = pcm_partner = None
    if has_tracks:
        me, pa = tmp / "me.wav", tmp / "partner.wav"
        extract_wav(src, TRACK_ME, me)
        extract_wav(src, TRACK_PARTNER, pa)
        pcm_me, pcm_partner = load_pcm(me), load_pcm(pa)

    words = []
    for chunk_words in run_chunks(mix, prompt, tmp, "Mix"):
        # Sprecher-Tags pro Block zuordnen (Tag-Nummern sind zwischen Blöcken nicht stabil)
        mapping = {}
        for spk in {w["spk"] for w in chunk_words}:
            if pcm_me is not None:
                sw = [w for w in chunk_words if w["spk"] == spk and w["end"] > w["start"]]
                e_me = sum(energy(pcm_me, w["start"], w["end"]) for w in sw)
                e_pa = sum(energy(pcm_partner, w["start"], w["end"]) for w in sw)
                mapping[spk] = names[0] if e_me >= e_pa else names[1]
            else:
                mapping[spk] = f"Sprecher {spk}"
        for w in chunk_words:
            w["name"] = mapping[w["spk"]]
        words += chunk_words
    return words, duration


def mode_tracks(src, tmp, prompt, names):
    words, duration = [], 0.0
    for track, name in ((TRACK_ME, names[0]), (TRACK_PARTNER, names[1])):
        wav = tmp / f"track{track}.wav"
        extract_wav(src, track, wav)
        duration = max(duration, wav_duration(wav))
        for chunk_words in run_chunks(wav, prompt, tmp, name, None):
            for w in chunk_words:
                w["name"] = name
            words += chunk_words
    return words, duration


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path, help="OBS-Aufnahme (.mkv, 3 Audiospuren) oder beliebige Audiodatei")
    ap.add_argument("--mode", choices=["mix", "tracks"], default="mix",
                    help="mix = Mix-Spur mit Sprecher-Tags (Standard), tracks = Spur 2 und 3 getrennt")
    ap.add_argument("--terms", default="", help='Kontextbegriffe, kommagetrennt, z. B. "SestigSystems, DigiKey"')
    ap.add_argument("--terms-file", type=Path, help="Datei mit Kontextbegriffen (eine pro Zeile oder kommagetrennt)")
    ap.add_argument("--me", default=NAME_ME, help=f"Name für Spur {TRACK_ME} (Standard: {NAME_ME})")
    ap.add_argument("--partner", default=NAME_PARTNER, help=f"Name für Spur {TRACK_PARTNER} (Standard: {NAME_PARTNER})")
    ap.add_argument("-o", "--output", type=Path, help="Markdown-Ausgabe (Standard: <input>.md)")
    ap.add_argument("--keep-audio", action="store_true", help="erzeugte WAV-Dateien neben der Ausgabe behalten")
    args = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} nicht gefunden")
    if not args.input.exists():
        sys.exit(f"Datei nicht gefunden: {args.input}")

    terms = [t.strip() for t in re.split(r"[,\n]", args.terms) if t.strip()]
    if args.terms_file:
        terms += [t.strip() for t in re.split(r"[,\n]", args.terms_file.read_text(encoding="utf-8"))
                  if t.strip() and not t.strip().startswith("#")]
    terms = list(dict.fromkeys(terms))
    prompt = (PROMPT_SPK if args.mode == "mix" else PROMPT_PLAIN) + (f" Context terms: {', '.join(terms)}." if terms else "")

    n_tracks = audio_track_count(args.input)
    has_tracks = n_tracks >= TRACK_PARTNER
    if args.mode == "tracks" and not has_tracks:
        sys.exit(f"Modus 'tracks' braucht {TRACK_PARTNER} Audiospuren, gefunden: {n_tracks}")
    if n_tracks < TRACK_MIX:
        sys.exit("keine Audiospur gefunden")
    print(f"{args.input.name}: {n_tracks} Audiospur(en), Modus {args.mode}", file=sys.stderr)

    names = (args.me, args.partner)
    with tempfile.TemporaryDirectory(prefix="transcribe_") as td:
        tmp = Path(td)
        if args.mode == "mix":
            words, duration = mode_mix(args.input, tmp, prompt, has_tracks, names)
        else:
            words, duration = mode_tracks(args.input, tmp, prompt, names)
        if args.keep_audio:
            for f in tmp.glob("*.wav"):
                if "_chunk" not in f.name:
                    shutil.copy(f, args.input.with_name(f"{args.input.stem}_{f.name}"))

    out = args.output or args.input.with_suffix(".md")
    write_markdown(out, args.input, args.mode, terms, build_turns(words), duration)
    print(f"Geschrieben: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()

# kanji-splash

A tiny terminal **start screen**: meaning, big ASCII art of a kanji, a classical haiku, and optional animations (embers, starlight, sakura, sunrays, grass).

Built for terminals that like a bit of theater — Kitty, Cool Retro Term, etc.

## Install

**Requirements:** Python 3.10+, [Pillow](https://pypi.org/project/Pillow/), a CJK-capable font (Noto CJK or IPA fonts on most Linux distros).

```bash
git clone https://github.com/YOUR_USERNAME/kanji-splash.git
cd kanji-splash

# dependency
pip install -r requirements.txt
# or on Debian/Ubuntu/Mint:
# sudo apt install python3-pil fonts-noto-cjk

# put commands on your PATH
mkdir -p ~/.local/bin
ln -sfn "$(pwd)/kanji_splash.py" ~/.local/bin/kanji-splash
ln -sfn "$(pwd)/kanji-new" ~/.local/bin/kanji-new
# ensure ~/.local/bin is on PATH (add to ~/.bashrc if needed):
# export PATH="$HOME/.local/bin:$PATH"

kanji-splash moon
```

### Run on every new terminal (optional)

Add to `~/.bashrc` (interactive shells only):

```bash
export PATH="$HOME/.local/bin:$PATH"
if [[ $- == *i* ]] && [[ "${KANJI_SPLASH:-1}" != "0" ]] && [[ -t 1 ]]; then
  command -v kanji-splash >/dev/null 2>&1 && kanji-splash
fi
```

Disable for one session: `KANJI_SPLASH=0 bash`.

## Quick start

```bash
# random kanji (same as kanji-splash -m random)
kanji-new

# or the full command
kanji-splash

# look up by English keyword (no Japanese input needed)
kanji-splash moon
kanji-splash dream
kanji-splash cherry

# specific character (if you can type it)
kanji-splash -c 桜

# list all kanji with their keywords
kanji-splash --list

# same kanji all day
kanji-splash -m daily

# styles & ramps
kanji-splash -s sakura -r blocks
kanji-splash -s ocean  -r ascii
kanji-splash -s moss   -r dots

# skip all animation (instant static print)
kanji-splash --no-animate

# fade-in only, no ongoing shimmer
kanji-splash --no-shimmer

# auto-stop shimmer after 5s (default: until any key)
kanji-splash --shimmer-sec 5

# more / fewer rising edge embers (0..1); kanji body stays mostly calm
kanji-splash --noise 0.8
kanji-splash --noise 0.2

# slower / faster fade (milliseconds)
kanji-splash --fade-ms 1200

# list everything in the data file
kanji-splash --list
```

On a real terminal the glyph **fades in**, then **keeps shimmering** (hue wave + density noise) until you press a key. Use `--no-animate` in scripts.

## Keyboard shortcuts (any terminal)

While the splash is up (including Cool Retro Term):

| Key | Action |
|-----|--------|
| `n` | new random kanji |
| `l` | list all kanji |
| `d` | today's daily kanji |
| `a` | cycle animation effect |
| `c` | cycle kanji ink color (12 steps) |
| `q` | quit (other keys also dismiss) |

Footer:

```text
sunrays  ·  pastel-blue
(n) new  ·  (l) list  ·  (d) daily  ·  (a) anim  ·  (c) color  ·  (q) quit
```

Ink colors (press `c`): red → pastel-red → orange → pastel-orange → yellow →
pastel-yellow → green → pastel-green → blue → pastel-blue → purple → pastel-purple → …

Each kanji also has a **default color** and **default animation** in `kanji.json`
(e.g. 桜 → sakura + pastel-red, 月 → starlight + pastel-yellow). Abstract kanji
use a random color/effect. `(a)` / `(c)` still override live; the next kanji
reloads its own defaults.

Effects (cycle with `a`):

| Effect | Look |
|--------|------|
| `embers` | Rising edge sparks |
| `starlight` | Sparse twinkling stars + soft breath |
| `sakura` | Falling cherry blossoms in the wind |
| `sunrays` | Warm light cascading over the glyph |
| `grass` | Meadow at the bottom, blades blowing in wind |

```bash
kanji-splash --effect sakura
kanji-splash moon --effect sunrays
kanji-splash cherry --effect sakura
```

## Layout

```
~/kanji-splash/
  kanji_splash.py   # the program
  kanji.json        # kanji + meanings + example words (edit freely)
  README.md
```

Installed as:

```
~/.local/bin/kanji-splash  →  ~/kanji-splash/kanji_splash.py
```

## Show on every new interactive shell

Add this near the end of `~/.bashrc` (only runs for interactive sessions):

```bash
# kanji start screen (skip in non-interactive / when KANJI_SPLASH=0)
if [[ $- == *i* ]] && [[ "${KANJI_SPLASH:-1}" != "0" ]]; then
  command -v kanji-splash >/dev/null && kanji-splash -m daily -s ember
fi
```

Temporarily silence it:

```bash
KANJI_SPLASH=0 bash   # one shell without splash
```

Or comment the block out of `.bashrc`.

## Add your own kanji

The list is **haiku-first**: classic Edo verses (芭蕉・蕪村・一茶), then kanji drawn from those lines.

Edit `kanji.json` — each entry looks like:

```json
{
  "char": "夢",
  "readings": { "on": ["ム"], "kun": ["ゆめ"] },
  "meaning": "dream; sleep-visions and ambitions alike",
  "haiku": {
    "lines": ["旅に病んで", "夢は枯野を", "かけめぐる"],
    "reading": "たびにやんで ゆめはかれのを かけめぐる",
    "translation": "Ill on a journey — / my dreams wander round / over withered fields",
    "author": "松尾芭蕉",
    "author_en": "Matsuo Bashō"
  }
}
```

Then `kanji-splash -c 夢`. See `kanji-splash --list` for the full set.

## Requirements

- Python 3
- Pillow (`python3-pil` — already common on Mint)
- A Japanese font (Noto CJK or IPA fonts — already on this machine)

## Flags

| Flag | Meaning |
|------|---------|
| `-c 道` | Force a character |
| `-m daily` / `-m random` | Pick mode |
| `-s ember\|ocean\|sakura\|mono\|moss` | Art color |
| `-r blocks\|ascii\|dots` | Density characters |
| `-w 40` | Art width |
| `--no-color` | Plain text |
| `--no-animate` | Instant static frame |
| `--no-shimmer` | Fade-in only, then freeze |
| `--shimmer-sec N` | Stop shimmer after N seconds (0 = keypress) |
| `--noise 0..1` | Edge embers + mild body grain (default 0.45) |
| `--fade-ms N` | Fade duration in ms (default 850) |
| `--list` | Show data file |

# kanji-splash

A terminal **start screen** with big ASCII-art kanji, a short English gloss, a classical haiku, and optional animations.

Works especially well in Kitty, Cool Retro Term, and other terminals that enjoy a bit of theater.

![requires Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![license MIT](https://img.shields.io/badge/license-MIT-green)

## Features

- **ASCII kanji art** rendered from a system CJK font (aspect-corrected for tall block cells)
- **Classical haiku** (芭蕉 · 蕪村 · 一茶) that use the displayed character
- **English keyword lookup** — no Japanese input method required  
  `kanji-splash moon` · `kanji-splash firefly` · `kanji-splash fart`
- **Animations:** embers, starlight, sakura, sunrays, grass (with bugs)
- **Per-kanji defaults** for ink color and animation (abstract kanji pick at random)
- **Keyboard controls** that work even without clickable hyperlinks
- **145+ kanji** in an editable JSON database

## Install

Quick install (Linux):
git clone https://github.com/zenzenzo/kanji-splash.git && cd kanji-splash
sudo apt install python3-pil fonts-noto-cjk
mkdir -p ~/.local/bin && ln -sfn "$(pwd)/kanji_splash.py" ~/.local/bin/kanji-splash && ln -sfn "$(pwd)/kanji-new" ~/.local/bin/kanji-new
Then run: kanji-splash

**Requirements**

- Python 3.10+
- [Pillow](https://pypi.org/project/Pillow/)
- A CJK font (e.g. Noto CJK or IPA fonts)

```bash
git clone https://github.com/zenzenzo/kanji-splash.git
cd kanji-splash

# dependency
pip install -r requirements.txt
# Debian / Ubuntu / Mint alternative:
# sudo apt install python3-pil fonts-noto-cjk

# put commands on your PATH
mkdir -p ~/.local/bin
ln -sfn "$(pwd)/kanji_splash.py" ~/.local/bin/kanji-splash
ln -sfn "$(pwd)/kanji-new" ~/.local/bin/kanji-new

# if needed, add to ~/.bashrc:
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

Disable one session: `KANJI_SPLASH=0 bash`

## Usage

```bash
kanji-splash              # random kanji
kanji-new                 # same as -m random
kanji-splash moon         # English keyword
kanji-splash -c 桜        # specific character
kanji-splash -m daily     # same pick all day
kanji-splash --list       # all kanji + keywords

kanji-splash --effect sakura
kanji-splash --color blue
kanji-splash --no-animate # static one-shot (scripts)
```

### Keyboard (while the splash is up)

| Key | Action |
|-----|--------|
| `(n)` | new random kanji |
| `(l)` | list all kanji |
| `(d)` | today's daily kanji |
| `(a)` | cycle animation |
| `(c)` | cycle ink color |
| `(q)` | quit |

Footer example:

```text
sakura  ·  pastel-red
(n) new  ·  (l) list  ·  (d) daily  ·  (a) anim  ·  (c) color  ·  (q) quit
```

### Animations (`(a)` or `--effect`)

| Effect | Look |
|--------|------|
| `embers` | Rising edge sparks |
| `starlight` | Sparse twinkling stars + soft breath |
| `sakura` | Falling cherry blossoms in the wind |
| `sunrays` | Warm light from the top-right, fading with distance |
| `grass` | Meadow at the bottom + three buzzing bugs |

### Ink colors (`(c)` or `--color`)

Cycle order:  
**red** → pastel-red → **orange** → pastel-orange → **yellow** → pastel-yellow →  
**green** → pastel-green → **blue** → pastel-blue → **purple** → pastel-purple → …

Many kanji ship with a default color and effect in `kanji.json` (e.g. 桜 → sakura + pastel-red).  
Abstract entries use random defaults. Live `(a)` / `(c)` overrides apply until the next kanji.

## Flags

| Flag | Meaning |
|------|---------|
| `keyword` | English keyword lookup (positional) |
| `-c 道` | Force a character |
| `-m daily` / `-m random` | Pick mode |
| `-s ember\|ocean\|sakura\|mono\|moss` | Legacy style palette (ink `--color` preferred) |
| `-r blocks\|ascii\|dots` | Density characters |
| `-w 40` | Art width (terminal columns, after aspect fix) |
| `--effect NAME` | Start with this animation |
| `--color NAME` | Start with this ink color |
| `--no-color` | Plain text |
| `--no-animate` | Instant static frame |
| `--no-shimmer` | Fade + typewriter only, then freeze |
| `--shimmer-sec N` | Auto-stop live effects after N seconds (0 = key) |
| `--noise 0..1` | Particle intensity (default 0.45) |
| `--fade-ms N` | Glyph fade duration in ms (default 850) |
| `--list` | Show all kanji and keywords |
| `--data PATH` | Alternate JSON database |

## Project layout

```text
kanji-splash/
  kanji_splash.py    # main program
  kanji-new          # wrapper → kanji-splash -m random
  kanji.json         # database (char, keyword, haiku, color, effect, …)
  requirements.txt
  LICENSE            # MIT
  README.md
```

## Add your own kanji

The list is **haiku-first**: classic verses, then characters drawn from those lines.

```json
{
  "char": "夢",
  "readings": { "on": ["ム"], "kun": ["ゆめ"] },
  "meaning": "dream; sleep-visions and ambitions alike",
  "keyword": "dream",
  "keywords": ["dream", "yume"],
  "color": "purple",
  "effect": "starlight",
  "haiku": {
    "lines": ["旅に病んで", "夢は枯野を", "かけめぐる"],
    "reading": "たびにやんで ゆめはかれのを かけめぐる",
    "translation": "Ill on a journey — / my dreams wander round / over withered fields",
    "author": "松尾芭蕉",
    "author_en": "Matsuo Bashō"
  }
}
```

- `color` / `effect`: one of the known names, or `null` for random  
- Then: `kanji-splash dream` or `kanji-splash -c 夢`

## Credits

Built with **[Grok](https://grok.com)** (xAI) doing all of the coding — from the splash renderer and animations to the haiku database and install docs.

Haiku are classical Japanese works (public domain). English translations are provided for convenience; improve them if you like.

## License

MIT — free to use, modify, and repurpose. See [LICENSE](LICENSE).

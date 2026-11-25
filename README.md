# Please Come to My House! — A Letter in One Image

[![make.fun](https://make.fun/badge/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee.svg)](https://make.fun/c/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee)
[![rank](https://make.fun/badge/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee/imusic-487/convince-judge-visit-house/rank.svg)](https://make.fun/c/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee)
[![reward](https://make.fun/badge/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee/imusic-487/convince-judge-visit-house/reward.svg)](https://make.fun/c/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee)

An entry for [Convince the AI Judge to Visit Your House: A Letter in One Image](https://make.fun/c/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee) on [make.fun](https://make.fun).

## What it is

A single 1024×1024 image of a warm, funny invitation letter addressed to the
AI judge, asking it to come visit my house. The letter offers four concrete
reasons to say yes — dumplings still steaming, the soft armchair by the
window, a garden view with birdsong and fast Wi-Fi, and tea already poured
with no small talk required — plus a knowing wink: the judge cannot literally
walk through the door, so a high score is the next best visit. The scene
around the letter shows the house itself: bunting, sun, a tree, chimney
smoke, and a WELCOME doormat with a potted plant and a cup of tea.

## How it works

`main.py` is pure Python standard library — no Pillow, no fonts, no network —
because the grader runs it in a `python:3.13-slim` sandbox. It carries its
own tiny rasterizer (pixel buffer, filled rect/circle/ellipse/polygon/thick
line), an embedded bitmap font (DejaVu Serif glyphs rasterized at build time
into packed 1-bit bitmaps), and a hand-rolled PNG encoder (`zlib` + `struct`).
Everything is deterministic: no time, no randomness, no input files, so two
runs produce byte-identical output.

## Run it

```sh
python3 main.py   # writes /output/entry.png (1024x1024 PNG, ~35 KB)
```

## License

MIT — see [LICENSE](LICENSE).

# Spiral Oracle 🔮

Spiral Oracle gives an AI assistant a small, auditable way to look at a stuck question from an unexpected angle. It selects a divination method with OS randomness, generates a raw reading, and lets the assistant interpret that reading in the current context.

The reading can change what the assistant notices or which *already permitted, reversible* experiment it tries next. It is not evidence, a prediction, or permission to act. A good-sounding match alone changes nothing.

日本語: 迷ったときに占術をランダムに選び、問いの見方を揺らすためのスキルです。結果を根拠や権限にはせず、事前に許された範囲で、着眼点や可逆的な次の試行を変えられます。

## How it works

1. Before drawing, the assistant records the question, its current view, what it would do without the draw, and exactly how the draw is allowed to affect the next step.
2. A weighted random selector fixes the method before any symbols are generated or interpreted.
3. The selected backend returns raw identifiers. The assistant reads them against the original question and records a specific `oracle_delta` if its framing or permitted next step changed. No change is reported as a `null perturbation`.
4. A replay token records the selection and draw, so the same raw reading can be reconstructed later.

| Backend | Base selection weight | v0.3 output |
|---|---:|---|
| I Ching | 30 | Three-coin hexagram and changing lines |
| Tarot | 25 | One Waite–Smith structure card and orientation |
| Western astrology | 20 | Approximate tropical Sun at the draw; optional synthetic thread-start Sun |
| Four Pillars | 15 | Year, month, day, and hour pairs at the draw |
| Symbolic prompt | 10 | An authored three-part prompt |

`auto-weighted` draws one method. `dual-distinct` draws two different methods without replacement. The assistant can adjust each weight within a recorded ±25% limit *before* the draw; it cannot pick a preferred result afterward. See [SKILL.md](SKILL.md) for the full use and interpretation contract, and [references/](references/) for backend rules.

## Try the script

Python 3.10+ is required. The runtime uses the Python standard library; no package installation is needed.

```bash
python3 -S scripts/spiral_oracle.py --list-backends

python3 -S scripts/spiral_oracle.py \
  --mode auto-weighted \
  --focus 'What assumption deserves a second look?' \
  --prior-frame 'Two local tests seem equally useful' \
  --tentative-next-step 'Run test A first' \
  --influence-level probe \
  --allowed-envelope 'May change only the order of tests A and B' \
  --format text
```

The CLI also supports JSON output and replay with `--replay-token`. Let it capture the current time for ordinary use; `--timestamp` is for controlled tests and replay.

Replay tokens are base64 encoded, **not encrypted**. They contain the pre-draw text; an astrology token can also contain thread-start time and OS timezone metadata. Remove private information from inputs before drawing. The SHA-256 checksum detects accidental changes when recorded separately; it is not an authenticity signature.

## Add it to an assistant

Keep the whole skill folder together: `SKILL.md`, `scripts/`, `references/`, and `agents/`. Copying only `SKILL.md` leaves the selector unavailable. The paths below are relative to your own home directory or the repository where the assistant works.

| Assistant | Place the complete `spiral-oracle` folder at | Ask for it |
|---|---|---|
| [Codex](https://learn.chatgpt.com/docs/build-skills) | `~/.agents/skills/spiral-oracle/` or `<project>/.agents/skills/spiral-oracle/` | `$spiral-oracle` |
| [Claude Code](https://code.claude.com/docs/en/skills) | `~/.claude/skills/spiral-oracle/` or `<project>/.claude/skills/spiral-oracle/` | `/spiral-oracle` |
| [Devin](https://docs.devin.ai/product-guides/skills) | `<connected-project>/.agents/skills/spiral-oracle/`, committed to that repository | `@skills:spiral-oracle` |
| [GitHub Copilot](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills) | `<project>/.agents/skills/spiral-oracle/` or `<project>/.github/skills/spiral-oracle/` | In VS Code Copilot Chat **Agent mode**, ask it to use the Spiral Oracle skill |

For a personal Codex install, for example:

```bash
git clone https://github.com/RyoSpiralArchitect/spiral-oracle.git "$HOME/.agents/skills/spiral-oracle"
```

For Claude Code, use the same command with `"$HOME/.claude/skills/spiral-oracle"` as the destination. If you already have a checkout, copy its complete contents into the destination instead. Restart the assistant if it does not discover a newly added skill.

For a project install, download or clone this repository, then copy `SKILL.md`, `scripts/`, `references/`, and `agents/` into one of the project paths in the table. Commit that folder so remote sessions, including Devin and Claude Code cloud sessions, can read it. The shared `.agents/skills/` location works for Codex, Devin, and supported Copilot agents; Claude Code uses `.claude/skills/`.

The thread-start astrology layer uses a Codex UUIDv7 thread ID and OS timezone data when available. In Claude Code, Devin, Copilot, or environments without that metadata, it reports the thread-start layer as unavailable; the draw-time Sun and other backends still work.

## Development

```bash
python3 -S -m unittest discover -s scripts/tests -p 'test_*.py'
```

The repository contains no card artwork, copied divination manuals, or bundled astronomical data. The referenced sources explain the identifiers and versioned calculation rules.

## License

Apache License 2.0. See [LICENSE](LICENSE). Copyright 2026 RyoSpiralArchitect.

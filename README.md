# DX Core 4 Dashboard

A small, self-contained tool that pulls a GitHub repo's PRs, CI runs, and
issues and turns them into the metrics DORA and DX's own **Core 4**
framework (Speed, Effectiveness, Quality, Impact) are built around —
including a first pass at flagging AI-assisted work and comparing its
cycle time against everything else.

I built this while applying for the Principal Solutions Architect role on
DX's Solutions Engineering team. It's not affiliated with, endorsed by, or
built using any non-public material from DX or Atlassian — it's an
independent, from-scratch reimplementation of publicly documented
methodology (the [DORA four keys](https://dora.dev) and DX's published
[Core 4 research](https://getdx.com/research/measuring-developer-productivity-with-the-dx-core-4/)),
against real GitHub data, to show I understand both the domain and the
implementation problems a customer-facing SA runs into: messy source APIs,
ambiguous proxy metrics, rate limits, and making the output legible to
someone who isn't going to read the code.

**[Live dashboard →](#deploying-the-dashboard)** (see below to enable GitHub Pages after you fork/push this)

## What it computes

**DORA four keys**, from PRs (lead time) and Actions runs (deploy
frequency, change failure rate) and bug-labeled issues (MTTR):

- Lead time for changes
- Deployment frequency
- Change failure rate
- Mean time to recovery

**Core 4-style breakdown** (Speed / Effectiveness / Quality / Impact),
built from the same data plus PR metadata:

- Speed: cycle time, PR throughput
- Effectiveness: deployment frequency (a proxy — real Effectiveness needs
  survey/DevEx data this tool doesn't have)
- Quality: change failure rate, revert rate
- Impact: % of merged PRs linked to an issue (a proxy — real Impact
  scoring needs planning-tool data like Jira/Linear)

**AI-assisted work detection**, via keyword/label heuristics
(`Co-authored-by: Claude`, Copilot mentions, `ai-assisted` labels, etc.),
compared against non-flagged work on cycle time. It's explicit about being
directional, not authoritative — it'll miss undisclosed AI usage and can
be fooled by noise.

Every proxy metric says so in its own output. I'd rather a metric admit
what it can't see than quietly overclaim — that's the same principle DX's
own research is built on.

## Try it

```bash
pip install -r requirements.txt
export GITHUB_TOKEN=ghp_xxx   # optional, raises the rate limit from 60/hr to 5000/hr
python -m dx_dashboard.cli --owner pallets --repo click --out data/report.json
cp data/report.json dashboard/report.json
python -m http.server -d dashboard 8000
# open http://localhost:8000
```

Run the tests:

```bash
pytest tests/ -v
```

## Deploying the dashboard

`.github/workflows/refresh-report.yml` runs weekly (and on-demand via
"Run workflow" in the Actions tab), regenerates `data/report.json` for
whatever `owner`/`repo` you configure, and publishes `dashboard/` to
GitHub Pages. Enable Pages in your fork's settings (Source: GitHub
Actions) and it'll pick up from there.

## How this was built

Built collaboratively with Claude (Anthropic's AI assistant) — I directed
the architecture and made the product calls (what to measure, which
proxies were honest vs. misleading, what the CLI/report contract should
look like); Claude wrote a chunk of the implementation. Commits where
Claude wrote the bulk of the code carry a `Co-authored-by: Claude`
trailer, same convention GitHub uses for Copilot. Check `git log` if
you want to see the actual split.

Given DX's whole product is about measuring human-AI collaboration in the
SDLC, it felt more honest — and frankly more relevant to the role — to
show that split plainly instead of pretending this was hand-written
top to bottom.

## Known limitations

- GitHub Actions workflow *runs* are used as a deployment-frequency proxy,
  since the REST API has no first-class "deployment" concept for most
  repos. If a repo doesn't deploy via Actions, this will read low even for
  a genuinely fast-moving project.
- Effectiveness and Impact are the weakest of the Core 4 categories here —
  they need planning-tool and survey data this tool doesn't pull.
- AI-assisted detection is keyword/label-based and will under-count.

## License

MIT — see `LICENSE`.

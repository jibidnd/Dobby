# Hosting dobby — VPS mirror + Syncthing

This is the **later** upgrade from laptop-primary: a small always-on VPS as a *second body* so dobby is reachable on mobile even when your laptop is off. One brain, two bodies:

- **Product** (skills, hooks, plugin, AGENTS, config) → **git** (`git pull` on both)
- **Personal content** (`memory/` + `knowledge/`) → **Syncthing** (laptop ↔ VPS)
- **Projects / code** → **not synced** — stay on the laptop (mobile/VPS is for life + thinking)

> dobby is light — the LLM runs via API, not on the box — so the smallest tier is plenty (**1 vCPU / 1–2 GB**).

---

## 0. Pick a host

*Prices are approximate — verify current before you buy (checked ~2026).*

| Host | ~Price/mo | Ease | Notes |
|---|---|---|---|
| **DigitalOcean** | ~$4–6 (Basic Droplet) | ★★★ easiest | Best hand-holding + tutorials; 1-click Ubuntu; great for a first VPS |
| **Hetzner Cloud** | ~€3.79 (CX22: 2 vCPU/4 GB) | ★★★ | **Best value.** US regions (Oregon, Ashburn) + EU; clean console |
| **AWS Lightsail** | ~$3.50–5 | ★★ | Predictable flat pricing; simpler face on AWS |
| **Vultr / Linode** | ~$2.50–5 | ★★ | Fine, simple |
| **Fly.io** | usage-based, small | ★★ | Dev-friendly but more concepts (machines, volumes) |
| **Oracle Cloud "Always Free"** | **free** | ★ | Genuinely free ARM VM (up to 4 vCPU/24 GB), but signup/availability is painful and it's ARM64 (verify opencode arm64 build) |

**Recommendation:** **DigitalOcean** if you want the smoothest first-time experience; **Hetzner CX22** if you want the best price/perf and don't mind a slightly barer console. Either way pick **Ubuntu 24.04 LTS**, 1–2 GB RAM.

---

## 1. Get the product onto the VPS (add a private git remote)

Your dobby repo is local-only today. To sync the *product* across machines, give it a **private** remote. Personal content is gitignored, so nothing sensitive leaves your machine.

On the **laptop**:

```bash
# create an EMPTY private repo on GitHub/GitLab first (no README), then:
cd C:\dev\dobby
git remote add origin git@github.com:<you>/dobby.git   # SSH or https
git push -u origin master
```

Confirm nothing personal is tracked (should print nothing):

```bash
git ls-files | grep -E '^(memory|knowledge)/|dobby\.local\.md$'
```

---

## 2. Base setup on the VPS

SSH in, then:

```bash
# create a non-root user (skip if your host already did)
sudo adduser dobby && sudo usermod -aG sudo dobby
su - dobby

sudo apt update && sudo apt -y upgrade
sudo apt -y install git curl python3 python-is-python3   # hooks are stdlib-only

# ^ python-is-python3 matters: the opencode plugin invokes `python` (not `python3`).
#   Ubuntu ships only `python3`, so without this (or PYTHON=/usr/bin/python3 in the
#   service env, step 6) the memory hooks silently no-op under systemd.

# Node (for the opencode plugin) — NodeSource LTS
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt -y install nodejs

# opencode
curl -fsSL https://opencode.ai/install | bash
# ensure ~/.opencode/bin (or the reported path) is on PATH; re-login if needed
opencode --version
```

Clone the product:

```bash
git clone git@github.com:<you>/dobby.git ~/dobby
```

---

## 3. Configure dobby on the VPS (headless)

```bash
cd ~/dobby
opencode        # then in chat: configure-dobby
```

`configure-dobby` will set `DOBBY_HOME`, `npm install` the plugin, wire global config, and set a permission tier. Two headless-specific notes:

- **Provider auth — use an API key** (simplest with no browser). Put it in `~/.dobby/.env`:
  ```
  ANTHROPIC_API_KEY=sk-ant-...
  ```
  (For Claude-*subscription* OAuth instead: run `opencode auth login` on your laptop, then copy `~/.local/share/opencode/auth.json` to the VPS at the same path.)
- **Skip the tool/vault acts** if you like — the vault gets populated by Syncthing in step 5.

---

## 4. Tailscale (private access — do this before exposing anything)

On the **VPS**:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up          # opens a login URL; authenticate to your tailnet
tailscale ip -4            # note the 100.x.y.z address — this is the VPS's private IP
```

Install Tailscale on your **laptop** and **phone** too (same account). Now all three are on one private mesh; nothing is exposed to the public internet.

---

## 5. Syncthing (mirror memory/ + knowledge/)

Install on **both** the VPS and the laptop.

**VPS (headless):**

```bash
sudo apt -y install syncthing
# run as a user service
systemctl --user enable --now syncthing || syncthing   # first run creates config
sudo loginctl enable-linger dobby                       # keep the user service alive after logout
```

The web UI listens on `127.0.0.1:8384`. Reach it over the tailnet with an SSH tunnel from the laptop:

```bash
ssh -L 8384:localhost:8384 dobby@<vps-tailscale-ip>
# then open http://localhost:8384 in your laptop browser
```

**Laptop:** install Syncthing (Windows: the SyncTrayzor bundle is easiest); its UI is at `http://localhost:8384`.

**Pair + share:**

1. In each Syncthing UI: **Actions → Show ID** to get the device ID.
2. On the laptop: **Add Remote Device** → paste the VPS device ID → accept the reciprocal prompt on the VPS UI.
3. On the laptop, add two folders and share each with the VPS device (Folder Type: **Send & Receive** on both sides):
   - Label `dobby-memory` → path `C:\dev\dobby\memory`
   - Label `dobby-knowledge` → path `C:\dev\dobby\knowledge`
4. On the VPS, **accept** the shared folders and set their paths to `~/dobby/memory` and `~/dobby/knowledge`.

First sync pushes your laptop's notes to the VPS. From here they stay mirrored live.

> **Discipline:** use one body at a time. If you write to both simultaneously, Syncthing keeps both as `*.sync-conflict-*` copies of `hot.md` — recoverable, but avoid it. hot.md's topic-upsert layout tolerates the occasional merge.

---

## 6. Run `opencode serve` as a service

Create `/etc/systemd/system/dobby.service` (`sudo`):

```ini
[Unit]
Description=dobby (opencode serve)
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Type=simple
User=dobby
WorkingDirectory=/home/dobby/dobby
Environment=DOBBY_HOME=/home/dobby/dobby
EnvironmentFile=/home/dobby/.dobby/serve.env
ExecStart=/home/dobby/.opencode/bin/opencode serve --hostname %i --port 4096
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Put secrets in `~/.dobby/serve.env` (mode 600) — the server password *and* the model key so the service has them:

```
OPENCODE_SERVER_PASSWORD=<a-long-random-string>
ANTHROPIC_API_KEY=sk-ant-...
PYTHON=/usr/bin/python3
```

> `PYTHON=/usr/bin/python3` is belt-and-suspenders for the `python` vs `python3` issue — systemd runs with a minimal PATH, so pin the interpreter the plugin shells out to. (Redundant if you installed `python-is-python3`, but harmless.)

Set `--hostname` to the **VPS's Tailscale IP** so it only listens on the private mesh (replace `%i` with the `100.x.y.z` from step 4 — or template it). Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dobby
systemctl status dobby
```

Belt-and-suspenders firewall (only SSH + Tailscale; never open 4096 publicly):

```bash
sudo ufw allow OpenSSH
sudo ufw allow in on tailscale0
sudo ufw --force enable
```

---

## 7. Connect your clients

From the **laptop** or **phone** OpenCode client, point at:

```
http://<vps-tailscale-ip>:4096
```

Username `opencode`, password = your `OPENCODE_SERVER_PASSWORD`. (On the laptop you can also just keep using local dobby for project work and only hit the VPS from the phone — your call.)

---

## 8. Backup (Syncthing is a mirror, not a backup)

Syncthing replicates deletes/corruption too. Add real versioned backup of the personal content — e.g. nightly `restic` to a bucket:

```bash
sudo apt -y install restic
restic -r s3:s3.<region>.backblazeb2.com/<bucket> init      # once
# nightly (cron/systemd timer):
restic -r s3:... backup /home/dobby/dobby/memory /home/dobby/dobby/knowledge
```

(Or `rclone` to Dropbox/B2. Store repo password + keys in `~/.dobby/`, mode 600.)

---

## 9. Smoke tests (before trusting it)

1. **Memory injects under `serve`** — connect a client, start a session, and confirm dobby recalls a recent hot.md item. Then check the plugin log:
   ```
   tail -f ~/.dobby/opencode-plugin.log
   ```
   You want to see `load DOBBY_HOME=… ok=true`, `config mcp from .mcp.json`, and per-message `inject session=…b knowledge=…b` lines. If you see `FAIL hooks/session_init.py` or `runPython missing`, that's the `python` interpreter problem (see steps 2 & 6). *Researched note:* `chat.message` and `experimental.chat.system.transform` are core message-pipeline hooks that fire in the server for any client, so this should work — but the `system.transform` hook is `experimental.`-namespaced, so if an opencode upgrade ever breaks memory injection, check whether that hook was renamed. (Doctrine via `instructions`/AGENTS.md loads regardless — only the dynamic memory ride the experimental hook.)
2. **Provider works headless** — send one prompt; confirm a model reply (auth key/OAuth is good).
3. **Syncthing round-trip** — `/jot` something on the laptop, confirm it appears in `~/dobby/memory/hot.md` on the VPS within seconds, and vice-versa.
4. **Survives reboot** — `sudo reboot` the VPS; confirm `dobby.service` and Syncthing come back and the client reconnects.

---

## Update flow (ongoing)

- **Product change:** commit on laptop → `git push` → on VPS `git pull` + restart `dobby.service` (`sudo systemctl restart dobby`).
- **Notes:** just happen (Syncthing).
- **dobby itself:** `git pull` — plain git.
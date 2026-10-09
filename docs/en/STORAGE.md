# Storage & Sync — AlexandriaSandwich

## Topology

| Role | Host | Storage & Service Role |
|------|------|------------------------|
| Storage / Web Portal | `synology.local` (192.168.1.8) | **Source of truth** for job data (`/volume1/docker/alexandria/data`), Traefik + Authelia Portal (`alexandria_ui`) |
| Compute | `alex.local` (192.168.1.239) | OCR worker (`alexandria_worker`), n8n; mounts NAS shares |
| Dev | Mac mini M2 / `hermes.local` | Code + local docker smoke tests |

## Canonical paths

On NAS and inside the worker container:

```text
/data/input/          raw scans (immutable-ish)
/data/processing/     scratch (preprocessed, hOCR, temp)
/data/output/         sandwich PDFs + markdown
```

Recommended NAS export layout (NFS):

```text
/volume1/alexandria/input
/volume1/alexandria/processing
/volume1/alexandria/output
```

## Mount model (preferred on alex.local)

NFS mount NAS exports → `/data/{input,processing,output}` on the worker host;  
Docker binds the same paths into `alexandria_worker`.

Fallback when NFS is unavailable: `scripts/sync_storage.sh` rsync over SSH.

## Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `AS_NAS_HOST` | `nas.local` | NAS hostname |
| `AS_NAS_USER` | `admin` | SSH user for rsync fallback |
| `AS_NAS_BASE` | `/volume1/alexandria` | Remote base path on NAS |
| `AS_LOCAL_DATA` | `/data` | Local base on alex.local / container |
| `AS_WORKER_HOST` | `alex.local` | Compute host |
| `AS_WORKER_USER` | `root` | SSH user on compute |

## Sync directions

| Command mode | Direction | Use |
|--------------|-----------|-----|
| `pull-input` | NAS → local | Fetch new scans before OCR |
| `push-output` | local → NAS | Publish finished PDFs/MD |
| `pull-all` | NAS → local | Full tree (bootstrap) |
| `push-processing` | local → NAS | Checkpoint intermediate work |
| `bidirectional-output` | rsync both ways (output only) | Cautious merge with `--update` |

**Never** blindly rsync `--delete` on `input/` from worker → NAS.

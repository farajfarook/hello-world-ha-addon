# Local development

Runs the add-on in Docker Desktop with a tiny fake Home Assistant around it, so
you can develop without a real HA install.

```
docker compose up --build
```

Open **http://localhost:8123**. It redirects to the add-on UI at the same kind of
ingress path HA uses.

## What runs

| Service      | Role |
|--------------|------|
| `addon`      | The real add-on image built from `hello_world/` (HA base image, bashio, s6) |
| `supervisor` | `dev/mock_supervisor.py`: fake Supervisor API (options read/save, schema validation, restart) |
| `ingress`    | nginx at `172.30.32.2`, the HA ingress IP that `server.py` requires, serving under `/api/hassio_ingress/dev/` |

Options are saved to `dev/data/options.json`. Delete that file to go back to the defaults.

## Dev loop

| Change | Do |
|--------|----|
| `server.py` / `run.sh` | `docker compose restart addon` (files are bind-mounted) |
| `Dockerfile` / new files | `docker compose up --build -d` |
| Logs | `docker compose logs -f addon` (and `supervisor` for API calls) |
| Stop | `docker compose down` |

The UI's **Save & restart** button really restarts the add-on container.

## Limits

This is a mock. It doesn't check `config.yaml` itself (manifest errors, ingress
settings, icons, translations); only the option schema is mirrored in
`mock_supervisor.py`, and you must update it there if you change the schema. Do a
final test on a real HA (Local add-ons) before releasing.

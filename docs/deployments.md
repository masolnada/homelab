# Deploying your own apps

How a program you wrote gets from a commit to a running container in the
homelab, without anything outside the network holding credentials to it.

## The model

```
app repo (GitHub)          homelab repo (this one)        VM
─────────────────          ───────────────────────        ──
commit + tag                                              deploy.sh (timer)
        │                                                   │ git pull
        │                  bump image tag in the ───────────┤
        │                  stack's compose file             │ build missing images
        └──────────────────────────────────────────────────►│ push to zot
                            git clone at that ref           │ compose up -d
```

Two git repos, two roles:

- the **app repo** holds source and a `Dockerfile`, and nothing else. It knows
  nothing about the homelab.
- the **homelab repo** decides what runs. The image tag committed in a stack's
  `docker-compose.yml` is the deployed version. That is the single source of
  truth.

Nothing pushes into the homelab. The VM pulls the homelab repo, pulls app
sources, builds locally, and stores the result in the local registry. No CI
service, no external account, and no inbound credentials exist anywhere in this
loop.

## The registry

`registry/` runs [zot](https://zotregistry.dev), an OCI-native registry that is
a single Go binary with no database.

It is published on `127.0.0.1:5000` only. That matters: the Docker daemon
treats loopback registries as insecure by default, so pushes and pulls work
over plain HTTP with no TLS, no daemon configuration, and no `docker login`.
The registry is not reachable from the LAN.

`registry.<DOMAIN>` serves the read-only web UI through Caddy. Caddy rejects
anything that is not `GET`/`HEAD`/`OPTIONS` with a 405, so the browsable route
can never be used to push.

Retention is automatic: the 10 most recently pushed tags per repository are
kept, untagged manifests are deleted, and garbage collection runs daily. No
manual `garbage-collect` chore.

## Deploying

```bash
# Everything: pull, build what's missing, apply every stack
ssh homelab "cd /opt/homelab && sudo ./deploy.sh"

# One stack
ssh homelab "cd /opt/homelab && sudo ./deploy.sh automation"

# Apply the current checkout without pulling
ssh homelab "cd /opt/homelab && sudo ./deploy.sh --no-pull"
```

A systemd timer runs the full reconcile every 10 minutes, so in practice
committing a tag bump *is* the deploy. Running it by hand only makes it happen
now instead of within 10 minutes.

`start.sh` still exists and is now just `deploy.sh --no-pull`.

## Adding a new app

1. In the app repo: add a `Dockerfile`, commit, and tag a release.

2. In `registry/apps.conf`, map the image name to the git URL:

   ```
   my-app https://github.com/masolnada/my-app.git
   ```

   If the Dockerfile is not at repository root, add relative build-context and
   Dockerfile columns:

   ```
   milverds-agent-inbox https://github.com/masolnada/milverds.git services/agent-inbox server/Dockerfile
   ```

3. In the stack's `docker-compose.yml`, add the service with a pinned tag:

   ```yaml
     my-app:
       image: localhost:5000/my-app:v1.2.0
       container_name: my-app
       restart: unless-stopped
       environment:
         - TZ=${TIMEZONE}
       networks:
         - proxy_net
   ```

   The tag must be a git ref — tag, branch, or commit — that exists in the app
   repo. `deploy.sh` finds this reference by scanning the compose files, so
   nothing else needs to be registered.

4. Commit. The next reconcile clones the repo at that ref, builds, pushes, and
   starts the container.

## Releasing a new version

```bash
# in the app repo
git tag v1.3.0 && git push --tags

# in the homelab repo
# edit the image tag in the stack's docker-compose.yml
git commit -am "chore: bump my-app to v1.3.0" && git push
```

That is the whole loop. Rollback is a `git revert` of the bump commit — the old
image is still in the registry, so the next reconcile just starts it again.

## Why tags and not `:latest`

A pinned tag means the running version is recorded in git history, rollback is
a revert, and a push to the app repo cannot silently change what is running in
the homelab. The cost is one extra commit per release, which is also the audit
trail.

## Notes and limits

- **Builds run on the VM**, sharing 4 cores with Immich, InfluxDB, Grafana and
  two Zigbee2MQTT instances. Fine for Node and Go; something heavier will be
  noticeable. If it becomes a problem, the build step is the piece to move to a
  dedicated VM — the compose files would not change, since the image reference
  is the only interface.
- **Build sources are cached** in `/var/tmp/homelab-build/<app>`. Safe to
  delete; it will re-clone.
- **An image already in the registry is never rebuilt.** Deploys after the
  first are a no-op unless a tag changed. Moving tags (like a branch name) are
  therefore *not* re-pulled — use immutable tags, or delete the tag from the
  registry to force a rebuild.
- **A failed build aborts the deploy** before any stack is applied, so a broken
  app cannot take down the rest of the homelab mid-reconcile.
- **`git pull --ff-only`** means local edits on the VM will block the timer
  rather than being silently overwritten.

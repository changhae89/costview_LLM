# AWS EC2 Bootstrap

This folder contains a bootstrap script for Ubuntu 24.04 EC2 instances used to deploy `costview-prd`.

## What it does

- Installs `git` and `docker`
- Enables Docker on boot
- Adds the current user to the `docker` group
- Creates a GitHub deploy key for private repository access
- Creates `~/costview-prd/.env` from a safe template
- Clones the repository over SSH

## Run

Upload or copy the script to the server, then run:

```bash
chmod +x ./infra/aws/ec2-bootstrap.sh
./infra/aws/ec2-bootstrap.sh
```

## Important

- After the deploy key is generated, register the contents of `~/.ssh/costview_github_deploy.pub`
  in the GitHub repository under `Settings > Deploy keys`.
- After the script finishes, either open a new SSH session or run `newgrp docker`
  so `docker` works without `sudo`.
- Update `~/costview-prd/.env` with real production values before running the container.

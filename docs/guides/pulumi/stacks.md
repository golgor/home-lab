# Stacks

A stack is an isolated instance of the Pulumi project with its own config
and state. Think of it as an environment — same code, different settings.

Each stack gets a `Pulumi.<stack>.yaml` file for stack-specific config.

## Managing stacks

```bash
pulumi stack init dev          # create a new stack
pulumi stack select dev        # switch to an existing stack
pulumi stack ls                # list all stacks (* marks the active one)
```

## How stacks are used in this project

The `dev` stack targets the local machine (Docker). When migrating to new
hardware, create a new stack with its own config:

```bash
pulumi stack init rpi
pulumi config set --secret postgres:password <new-password>
pulumi up
```

Both stacks can run side by side during migration. Once validated, clean
up the old one:

```bash
pulumi stack select dev
pulumi destroy
```

## State

State is stored locally (`pulumi login --local`) in `~/.pulumi/`. This
is a one-time setup per machine:

```bash
pulumi login --local
```

!!! warning "State is local only"
    The `~/.pulumi/` directory only exists on the machine where you ran
    `pulumi up`. If migrating machines, copy `~/.pulumi/` or start fresh
    with `pulumi stack init`.

The `Pulumi.<stack>.yaml` files are committed to Git — they contain only
config values (secrets are encrypted).

import os


def validate_config(ctx, required_envs=None, required_secrets=None, secrets=None):
    missing = []

    for key in (required_envs or []):
        if os.environ.get(key):
            ctx.logger.info(f"ℹ️ {key}=set")
        else:
            ctx.logger.warning(f"⚠️ {key}=NOT SET")
            missing.append(key)

    for key in (required_secrets or []):
        if (secrets or {}).get(key, ""):
            ctx.logger.info(f"ℹ️ {key}=set")
        else:
            ctx.logger.warning(f"⚠️ {key}=NOT SET")
            missing.append(key)

    if missing:
        raise ValueError(f"Missing required config: {', '.join(missing)}")

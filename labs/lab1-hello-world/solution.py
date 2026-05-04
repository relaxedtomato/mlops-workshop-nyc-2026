import os

def init(ctx):
    greeting = os.environ.get('GREETING', 'Hello!')
    ctx.logger.info(f"Initialized with greeting: {greeting}")

def handler(ctx, event):
    ctx.logger.info(f"Handler triggered: {event}")
    return "Hello Vast Data"

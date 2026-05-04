# Lab 1: Hello Vast Data (20 min)

## Overview

Get acquainted with the DataEngine development flow: scaffold a function from scratch, understand the init/handler model, and deploy a scheduled pipeline end-to-end. Minimal coding; maximum platform familiarity.

```
  Schedule Trigger (every 5 min)
            │
            ▼
  ┌─────────────────────────┐
  │   DataEngine Pipeline   │
  │  ┌─────────────────────┐│
  │  │     Function        ││
  │  │  init(ctx)          ││ ← reads GREETING env var
  │  │  handler(ctx, event)││ ← logs greeting,
  │  │                     ││   returns response
  │  └─────────────────────┘│
  └─────────────────────────┘
            │
            ▼
     vastde logs tail
  ("Hello, World!" on schedule)
```

## Scenario

You've just joined the engineering team at **FrameIQ**, a startup building AI-powered video intelligence pipelines. Before touching any real data, you need to know how the platform works end-to-end. This lab walks you through the full flow using the simplest possible example.

> All commands run on the **workshop VM** via the terminal in your browser. Nothing runs on your laptop.

## Steps

### Step 1: Scaffold a new function

#### 1a. Check the CLI is available

```sh
vastde --help
```

#### 1b. Scaffold a new function using your username as a prefix

```sh
vastde functions init python-pip $USER-hello-world
cd $USER-hello-world
```

This generates the boilerplate directory:

```
$USER-hello-world/
├── main.py               ← your function logic
├── requirements.txt      ← Python dependencies
├── config.yaml           ← env vars for local dev
└── pipeline-config.yaml  ← pipeline definition (trigger, function, links)
```

> **Why $USER?** In a shared environment, prefixing with your username keeps your resources from colliding with others.

---

### Step 2: Write the greeting

Update `main.py`:

```python
import os

def init(ctx):
    greeting = os.environ.get('GREETING', 'Hello!')
    ctx.logger.info(f"Initialized with greeting: {greeting}")

def handler(ctx, event):
    ctx.logger.info(f"Handler triggered: {event}")
    return "Hello Vast Data"
```

---

### Step 3: Build and run locally

> **TODO:** Add clear visual distinction throughout this lab (and all labs) between code to copy into a file vs. CLI commands to run in the terminal.

Build the function image:

```sh
vastde functions build $USER-hello-world
```

Expected output:

```
Detected language: python
Validating Python version 3.12.*...
Python version 3.12.* resolved to 3.12.12
Building $USER-hello-world:latest
App Path: .../lab1-hello-world
Handlers File: main.py
2026/03/18 14:22:18 [Started] Python Builder: $USER-hello-world:latest
2026/03/18 14:22:34 [Completed] Python Builder: $USER-hello-world:latest
Build completed: $USER-hello-world:latest
```

Then run locally:

```sh
vastde functions localrun $USER-hello-world -c config.yaml
```

Expected output:

```
Function is starting on port 8080... Once ready, you can invoke it:

2026-04-17 16:42:47 [INFO] Vast Runtime, Version: 0.1.0+edaa62cc6748
2026-04-17 16:42:47 [INFO] Starting Vast Runtime
2026-04-17 16:42:47 [INFO] Runtime is listening on port 8080
2026-04-17 16:42:47 [INFO] Call Init Handler: init
```

In a second terminal:

```sh
vastde functions invoke --generate-event --url http://localhost:8080/
```

Expected output:

```
Generated CloudEvent with type: vastdata.com:Element.ObjectCreated
Sending CloudEvent to http://localhost:8080/
Event ID: 537d53e4-f7d4-49de-86c4-a4e49d1992a6
Event Type: vastdata.com:Element.ObjectCreated
CloudEvent sent successfully (Status: 204)
```

---

### Step 4: Build, tag, and push

> **TODO:** Document how registry env vars (`DE_REG_HOST`, `DE_REG_USER`, `DE_REG_NAME`) are provided and set up in the workshop environment.

```sh
vastde functions build $USER-hello-world
```

Expected output for `vastde functions build`:

```
Detected language: python
Validating Python version 3.12.*...
Python version 3.12.* resolved to 3.12.12
Building $USER-hello-world:latest
App Path: .../lab1-hello-world
Handlers File: main.py
Build log: .../lab1-hello-world/build.log
2026/03/18 14:22:18 [Started] Python Builder: $USER-hello-world:latest
2026/03/18 14:22:34 [Completed] Python Builder: $USER-hello-world:latest
Build completed: $USER-hello-world:latest
Build log saved to: .../lab1-hello-world/build.log
```

Tag and push to the workshop registry:

```sh
docker tag $USER-hello-world:latest $DE_REG_HOST/$DE_REG_USER/$USER-hello-world:latest
docker push $DE_REG_HOST/$DE_REG_USER/$USER-hello-world:latest
```
---

### Step 5: Create the function in DataEngine (CLI)

Register the function using the image you just pushed:

```sh
vastde functions create \
  --name $USER-hello-world \
  --container-registry $DE_REG_NAME \
  --artifact-source $DE_REG_USER/$USER-hello-world \
  --image-tag v1
```

Expected output:

```
Function created: $USER-hello-world
Name: $USER-hello-world
Tags: []
GUID: <guid>
Owner: [id: <id>, id-type: vid]
VRN: vast:dataengine:functions:$USER-hello-world
Last Revision: 1
```

Verify:

```sh
vastde functions list | grep $USER
```

Expected output:

```
Function Name              Description                          Guid                                    Updated at
---------------------------------------------------------------------------------------------------------------------------
$USER-hello-world                                               cf82b693-5483-4490-8a01-29f44e948149    2026-03-18 18:50
```

---

### Step 6: Create a scheduled trigger (UI)

Navigate to **DataEngine UI > Triggers > Create Trigger**.

![alt text](set-up-trigger.png)

Verify via CLI:

```sh
vastde triggers list | grep $USER
```

Expected output:

```
Trigger Name                    Status   Type   Description               GUID                        Updated at
---------------------------------------------------------------------------------------------------------------------
$USER-schedule-5m-trigger       Ready    ...    Schedule trigger...       4d32fd72-7961-4b00-940b...  2026-03-29 21:23
```

---

### Step 7: Create and deploy the pipeline (UI)

Navigate to **DataEngine UI > Pipelines > Create Pipeline**:

![Create and deploy pipeline](pipeline-configuration.png)

Update the environment variables to include `GREETING` variable:

![Create and deploy pipeline](pipeline-environment.png)

Connect the trigger to the function to create the pipeline:

![Create and deploy pipeline](trigger-function-pipeline.png)

Click deploy and wait for `Ready` status before proceeding.

You can also verify via CLI:

```sh
vastde pipelines list | grep $USER
```

---

### Step 8: Tail the logs

Stream logs from the deployed pipeline:

```sh
vastde logs tail $USER-hello-world-pipeline \
  --function $USER-hello-world \
  --since 1h
```

Wait up to 5 minutes for the schedule to fire. You should see:

```
2026-03-30 11:25:01.22 [$USER-hello-world] [INFO]  [user] Handler {'attributes': {'source': 'vastdata.com:schedule-5m-trigger...', 'type': 'vastdata.com:Schedule.TimerElapsed', 'specversion': '1.0', 'time': '2026-03-30T15:25:00...', 'cronschedule': '0 0/5 * ? * * *', ...}, 'data': {'message': 'Activating trigger by cron'}}
```

---

## Key Takeaways

- **init/handler model**: `init()` runs once at cold start; `handler()` runs on every event
- **ctx.logger**: the right way to emit logs; visible via `vastde logs tail`
- **os.environ**: env vars are set on the pipeline, not the function
- **$USER namespacing**: always prefix resource names in shared environments
- **Pipeline = trigger + function + links**: the pipeline wires it all together

---

**Next up: [Lab 2: Connect to S3](../lab2-s3-connect/)**

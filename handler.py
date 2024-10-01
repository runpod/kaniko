import runpod
import subprocess

def build_image(job):
    job_input = job["input"]
    context = job_input["context"]
    dockerfile_path = job_input["dockerfile_path"]
    destination = job_input["destination"]
    
    subprocess.run(["curl", "-fsSL", "https://bun.sh/install", "|", "bash"])
    subprocess.run(["/kaniko/executor", "--context={}".format(context), "--dockerfile={}".format(dockerfile_path), "--destination={}".format(destination), "--no-push", "--tarPath=/runpod-volume/image.tar"])
    subprocess.run("bun install", cwd="/kaniko/serverless-registry/push", shell=True)

    envs = { "USERNAME_REGISTRY": "pierre-bastola", "TAR_PATH": "/runpod-volume/image.tar" }
    subprocess.run("echo Innovator81@ | bun run index.ts r2-registry-production.pierre-bastola.workers.dev/runpod8:latest", cwd="/kaniko/serverless-registry/push", shell=True, env=envs)

    return True


runpod.serverless.start({"handler": build_image})
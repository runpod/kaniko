import runpod
import subprocess

def build_image(job):
    job_input = job["input"]
    context = job_input["context"]
    dockerfile_path = job_input["dockerfile_path"]
    destination = job_input["destination"]
    
    subprocess.run("curl -fsSL https://bun.sh/install | bash", shell=True, executable="/bin/bash")
    subprocess.run(["/kaniko/executor", "--context={}".format(context), "--dockerfile={}".format(dockerfile_path), "--destination={}".format(destination), "--no-push", "--tarPath=/runpod-volume/image.tar"])
    envs = { "USERNAME_REGISTRY": "pierre-bastola", "TAR_PATH": "/runpod-volume/image.tar" }
    subprocess.run("curl -fsSL https://bun.sh/install | bash && source /root/.bashrc && bun install && echo Innovator81@ | source /root/.bashrc && bun run index.ts r2-registry-production.pierre-bastola.workers.dev/runpod8:latest", cwd="/kaniko/serverless-registry/push", env=envs, shell=True, executable="/bin/bash")

    # subprocess.run("echo Innovator81@ | source /root/.bashrc && bun run index.ts r2-registry-production.pierre-bastola.workers.dev/runpod8:latest", cwd="/kaniko/serverless-registry/push", shell=True, env=envs, executable="/bin/bash")

    return True


runpod.serverless.start({"handler": build_image})
import runpod
import subprocess

def build_image(job):
    job_input = job["input"]
    context = job_input["context"]
    dockerfile_path = job_input["dockerfile_path"]
    destination = job_input["destination"]
    
    subprocess.run(["/kaniko/executor", "--context={}".format(context), "--dockerfile={}".format(dockerfile_path), "--destination={}".format(destination), "--no-push", "--tarPath=/runpod-volume/image.tar"])
    subprocess.run(["bun", "install"], cwd="/kaniko/serverless-registry/push")
    subprocess.run(["TAR_PATH=/runpod-volume/image.tar", "echo", "Innovator81@", "|", "USERNAME_REGISTRY=pierre", "bun", "run", "index.ts", "r2-registry-production.pierre-bastola.workers.dev/runpod8:latest"], cwd="/kaniko/serverless-registry/push")



    # subprocess.run(["/kaniko/executor", "--context={}".format(context), "--dockerfile={}".format(dockerfile_path), "--destination={}".format(destination), "--no-push", "--tarPath=/runpod-volume/image.tar"])
    # subprocess.run(["bun", "install"], cwd="serverless-registry/push")
    # subprocess.run(["TAR_PATH=/runpod-volume/image.tar", "echo", "Innovator81@", "|", "USERNAME_REGISTRY=pierre", "bun", "run", "index.ts", "r2-registry-production.pierre-bastola.workers.dev/runpod8:latest"], cwd="serverless-registry/push")


    # subprocess.run(["/runpod-volume/kaniko/executor", "--context={}".format(context), "--dockerfile={}".format(dockerfile_path), "--destination={}".format(destination), "--no-push", "--tarPath=/runpod-volume/image.tar"])
    # subprocess.run(["bun", "install"], cwd="/runpod-volume/kaniko/serverless-registry/push")
    # subprocess.run(["TAR_PATH=/runpod-volume/image.tar", "echo", "Innovator81@", "|", "USERNAME_REGISTRY=pierre", "bun", "run", "index.ts", "r2-registry-production.pierre-bastola.workers.dev/runpod8:latest"], cwd="/runpod-volume/kaniko/serverless-registry/push")

runpod.serverless.start({"handler": build_image})
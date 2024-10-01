import runpod
import subprocess
import os

def build_image(job):
    job_input = job["input"]
    context = job_input["context"]
    dockerfile_path = job_input["dockerfile_path"]
    destination = job_input["destination"]
    uuid = job_input["uuid"]

    envs = os.environ.copy()
    install_command = "curl -fsSL https://bun.sh/install | bash"
    subprocess.run(install_command, shell=True, executable="/bin/bash", env=envs)

    bun_bin_dir = os.path.expanduser("~/.bun/bin")
    envs["PATH"] = f"{bun_bin_dir}:{envs['PATH']}"

    subprocess.run(["/kaniko/executor", "--context={}".format(context), "--dockerfile={}".format(dockerfile_path), "--destination={}".format(destination), "--no-push", "--tarPath=/runpod-volume/image.tar"])
    envs["USERNAME_REGISTRY"] = "pierre-bastola"
    envs["TAR_PATH"] = "/runpod-volume/image.tar"
    envs["UUID"] = uuid
    subprocess.run("mkdir -p /runpod-volume/{}".format(uuid), shell=True, env=envs)
    subprocess.run("bun install", cwd="/kaniko/serverless-registry/push", env=envs, shell=True, executable="/bin/bash")
    run_command = "echo Innovator81@ | USERNAME_REGISTRY=pierre bun run index.ts r2-registry-production.pierre-bastola.workers.dev/runpod8:latest"
    subprocess.run(run_command, cwd="/kaniko/serverless-registry/push", env=envs, shell=True, executable="/bin/bash")

    return True


runpod.serverless.start({"handler": build_image})
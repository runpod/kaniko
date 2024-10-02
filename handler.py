import runpod
import subprocess
import os

def build_image(job):
    job_input = job["input"]
    context = job_input["context"]
    dockerfile_path = job_input["dockerfile_path"]
    destination = job_input["destination"]
    cloudflare_destination = job_input["cloudflare_destination"]
    uuid = job_input["uuid"]

    envs = os.environ.copy()
    install_command = "curl -fsSL https://bun.sh/install | bash"
    subprocess.run(install_command, shell=True, executable="/bin/bash", env=envs)

    bun_bin_dir = os.path.expanduser("~/.bun/bin")
    envs["PATH"] = f"{bun_bin_dir}:{envs['PATH']}"

    subprocess.run("mkdir -p /runpod-volume/{}".format(uuid), shell=True, env=envs)
    tarPath = "/runpod-volume/{uuid}/image.tar".format(uuid=uuid)
    subprocess.run(["/kaniko/executor", "--context={}".format(context), "--dockerfile={}".format(dockerfile_path), "--destination={}".format(destination), "--no-push", "--use-new-run", "--compressed-caching=false", "--tar-path={}".format(tarPath)])
    envs["USERNAME_REGISTRY"] = "pierre-bastola"
    envs["TAR_PATH"] = tarPath
    envs["UUID"] = uuid
    
    subprocess.run("bun install", cwd="/kaniko/serverless-registry/push", env=envs, shell=True, executable="/bin/bash")
    run_command = "echo Innovator81@ | USERNAME_REGISTRY=pierre bun run index.ts {}".format(cloudflare_destination)
    subprocess.run(run_command, cwd="/kaniko/serverless-registry/push", env=envs, shell=True, executable="/bin/bash")
    print(job_input)
    return True


runpod.serverless.start({"handler": build_image})
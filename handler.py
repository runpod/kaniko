import runpod
import subprocess
import os

def build_image(job):
    job_input = job["input"]
    dockerfile_path = job_input["dockerfile_path"]
    uuid = job_input["uuid"]
    cloudflare_destination = job_input["cloudflare_destination"]
    github_repo = job_input["github_repo"]    

    envs = os.environ.copy()
    install_command = "curl -fsSL https://bun.sh/install | bash"
    subprocess.run(install_command, shell=True, executable="/bin/bash", env=envs)

    bun_bin_dir = os.path.expanduser("~/.bun/bin")
    envs["PATH"] = f"{bun_bin_dir}:{envs['PATH']}"

    
    subprocess.run("mkdir -p /runpod-volume/{}".format(uuid), shell=True, env=envs)

    contextPath = "/runpod-volume/{}/repo.tar.gz".format(uuid)
    subprocess.run("git clone {} /runpod-volume/{}/repo".format(github_repo, uuid), shell=True)
    subprocess.run("tar -czvf {} /runpod-volume/{}/repo".format(contextPath, uuid), shell=True)

    imageBuildPath = "/runpod-volume/{}/image.tar".format(uuid)
    subprocess.run([
        "/kaniko/executor", 
        "--context={}".format("dir://{}".format(contextPath)), 
        "--dockerfile={}".format(dockerfile_path), 
        "--destination={}".format(cloudflare_destination), 
        "--no-push", "--tar-path={}".format(imageBuildPath)]
    )
    envs["USERNAME_REGISTRY"] = "pierre-bastola"
    envs["TAR_PATH"] = imageBuildPath
    envs["UUID"] = uuid
    
    subprocess.run("bun install", cwd="/kaniko/serverless-registry/push", env=envs, shell=True, executable="/bin/bash")
    run_command = "echo Innovator81@ | USERNAME_REGISTRY=pierre bun run index.ts {}".format(cloudflare_destination)
    subprocess.run(run_command, cwd="/kaniko/serverless-registry/push", env=envs, shell=True, executable="/bin/bash")
    
    return True

runpod.serverless.start({"handler": build_image})
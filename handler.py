import runpod
import subprocess
import os
import requests
import tarfile
import io

def build_image(job):
    job_input = job["input"]
    dockerfile_path = job_input["dockerfile_path"]
    build_id = job_input["build_id"]
    cloudflare_destination = job_input["cloudflare_destination"]
    github_repo = job_input["github_repo"]
    github_repo = github_repo.replace(".git", "")
    auth_token = job_input["auth_token"]
    ref = job_input["ref"]
    jwt_token = job_input["jwt_token"]
    username_registry = job_input["username_registry"]
    refresh_worker = job_input.get("refresh_worker", "true")
    refresh_worker_flag = True
    if refresh_worker == "false":
        refresh_worker_flag = False

    return_payload = {
        "refresh_worker": refresh_worker_flag,
        "token": jwt_token,
        "status": "succeeded",
        "build_id": build_id
    }

    envs = os.environ.copy()

    api_url = f"https://api.github.com/repos/{github_repo.split('/')[-2]}/{github_repo.split('/')[-1]}/tarball/{ref}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {auth_token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    try:
        response = requests.get(api_url, headers=headers, stream=True)
        response.raise_for_status()
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload

    temp_dir = f"/runpod-volume/{build_id}/temp"
    try:
        os.makedirs(temp_dir, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
            tar.extractall(path=temp_dir)
        extracted_dir = next(os.walk(temp_dir))[1][0]
        install_command = "curl -fsSL https://bun.sh/install | bash"
        subprocess.run(install_command, shell=True, executable="/bin/bash", check=True, env=envs)
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload

    bun_bin_dir = os.path.expanduser("~/.bun/bin")
    envs["PATH"] = f"{bun_bin_dir}:{envs['PATH']}"
    repoDir = "/runpod-volume/{}/temp/{}".format(build_id, extracted_dir)
    try:
        subprocess.run("mkdir -p /runpod-volume/{}".format(build_id), shell=True, env=envs, check=True)
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload
    
    try:
        subprocess.run("mkdir -p /runpod-volume/{}/cache".format(build_id), shell=True, env=envs, check=True)
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload

    imageBuildPath = "/runpod-volume/{}/image.tar".format(build_id)
    try:
        subprocess.run([
            "/kaniko/executor", 
            "--context={}".format("dir://{}".format(repoDir)), 
            "--dockerfile={}".format(dockerfile_path), 
            "--destination={}".format(cloudflare_destination), 
            # "--cache=true",
            # "--cache-dir={}".format(f"/runpod-volume/{build_id}/cache"),
            "--no-push", "--tar-path={}".format(imageBuildPath)
        ], check=True, env=envs)
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload
    
    envs["USERNAME_REGISTRY"] = username_registry
    envs["TAR_PATH"] = imageBuildPath
    envs["build_id"] = build_id
    envs["REGISTRY_JWT_TOKEN"] = jwt_token
    try:
        subprocess.run("bun install", cwd="/kaniko/serverless-registry/push", env=envs, shell=True, executable="/bin/bash")
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload

    run_command = "bun run index.ts {}".format(cloudflare_destination)
    try:
        subprocess.run(run_command, cwd="/kaniko/serverless-registry/push", env=envs, shell=True, check=True, executable="/bin/bash")
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload
    
    try:
        subprocess.run("rm -rf /runpod-volume/{}".format(build_id), shell=True, env=envs, check=True)
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload

    return return_payload

runpod.serverless.start({"handler": build_image})
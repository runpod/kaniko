import runpod
import subprocess
import os
import requests
import tarfile
import io
import logging

import re

def get_workdirs_from_dockerfile(file_path):
    workdirs = []
    with open(file_path, 'r') as dockerfile:
        for line in dockerfile:
            # Check for lines that contain the WORKDIR directive
            match = re.match(r"^\s*WORKDIR\s+(.+)", line, re.IGNORECASE)
            if match:
                # Extract the directory path
                workdir = match.group(1).strip()
                workdirs.append(workdir)
    return workdirs

impossible_workdirs = [
    "/root", "/", "/runpod-volume", "/lib", 
    "/opt", "/run", "/sbin", "/sys", "/var", 
    "/bin", "/dev", "/home", "/lib32", "/media", 
    "/proc", "/srv", "/tmp", "/workspace", "/boot", 
    "/etc", "/kaniko", "/lib64", "/mnt"]

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
    print(job_input)

    return_payload = {
        "refresh_worker": refresh_worker_flag,
        "token": jwt_token,
        "status": "succeeded",
        "build_id": build_id,
        "image_name": cloudflare_destination
    }

    envs = os.environ.copy()

    logging.info(f"Downloading {github_repo} at {ref}")
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

    logging.info(f"Extracting {github_repo} at {ref}")
    temp_dir = f"/runpod-volume/{build_id}/temp"
    try:
        os.makedirs(temp_dir, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
            tar.extractall(path=temp_dir)
        extracted_dir = next(os.walk(temp_dir))[1][0]
        install_command = "curl -fsSL https://bun.sh/install | bash"
        subprocess.run(install_command, shell=True, executable="/bin/bash", check=True, capture_output=True, env=envs)
    except subprocess.CalledProcessError as e:
        error_msg = str(e.stderr)
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e) + error_msg
        return return_payload
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload

    logging.info("Installing bun")
    bun_bin_dir = os.path.expanduser("~/.bun/bin")
    envs["PATH"] = f"{bun_bin_dir}:{envs['PATH']}"
    repoDir = "/runpod-volume/{}/temp/{}".format(build_id, extracted_dir)
    try:
        subprocess.run("mkdir -p /runpod-volume/{}".format(build_id), shell=True, env=envs, check=True)
    except subprocess.CalledProcessError as e:
        error_msg = str(e.stderr)
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e) + error_msg
        return return_payload
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload
    
    try:
        workdirs = get_workdirs_from_dockerfile(repoDir + "/" + dockerfile_path)
        logging.info(f"Workdirs: {workdirs}")
        for workdir in workdirs:
            if workdir in impossible_workdirs:
                return_payload["status"] = "failed"
                return_payload["error_msg"] = f"Workdir {workdir} is not allowed. Please change the workdir in your Dockerfile."
                return return_payload
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload
    
    logging.info("Creating cache directory")
    try:
        subprocess.run("mkdir -p /runpod-volume/{}/cache".format(build_id), shell=True, env=envs, check=True)
    except subprocess.CalledProcessError as e:
        error_msg = str(e.stderr)
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e) + error_msg
        return return_payload
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload

    logging.info("Building image")
    imageBuildPath = "/runpod-volume/{}/image.tar".format(build_id)
    try:
        subprocess.run([
            "/kaniko/executor", 
            "--context={}".format("dir://{}".format(repoDir)), 
            "--dockerfile={}".format(dockerfile_path), 
            "--destination={}".format(cloudflare_destination), 
            # "--cache=true",
            # "--cache-dir={}".format(f"/runpod-volume/{build_id}/cache"),
            "--single-snapshot",
            "--no-push", "--tar-path={}".format(imageBuildPath)
        ], check=True, env=envs)
    except subprocess.CalledProcessError as e:
        error_msg = str(e.stderr)
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e) + error_msg
        logging.error(f"Error building image: {str(e)} {error_msg}")
        return return_payload
    except Exception as e:
        logging.error(f"Error building image: {str(e)}")
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload

    logging.info("Installing dependencies")
    envs["USERNAME_REGISTRY"] = username_registry
    envs["TAR_PATH"] = imageBuildPath
    envs["UUID"] = build_id
    envs["REGISTRY_JWT_TOKEN"] = jwt_token
    try:
        subprocess.run("bun install", cwd="/kaniko/serverless-registry/push", env=envs, shell=True, executable="/bin/bash")
    except subprocess.CalledProcessError as e:
        error_msg = str(e.stderr)
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e) + error_msg
        return return_payload
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload

    logging.info("Pushing image to registry")
    run_command = "bun run index.ts {}".format(cloudflare_destination)
    try:
        subprocess.run(run_command, cwd="/kaniko/serverless-registry/push", env=envs, shell=True, check=True, executable="/bin/bash")
    except subprocess.CalledProcessError as e:
        error_msg = str(e.stderr)
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e) + error_msg
        return return_payload
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload
    
    logging.info(f"Cleaning up")
    try:
        subprocess.run("rm -rf /runpod-volume/{}".format(build_id), shell=True, env=envs, check=True)
    except subprocess.CalledProcessError as e:
        error_msg = str(e.stderr)
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e) + error_msg
        return return_payload
    except Exception as e:
        return_payload["status"] = "failed"
        return_payload["error_msg"] = str(e)
        return return_payload

    return return_payload

runpod.serverless.start({"handler": build_image})
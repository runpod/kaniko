import runpod
import subprocess

def build_image(job):

    job_input = job["input"]
    context = job_input["context"]
    dockerfile_path = job_input["dockerfile_path"]
    destination = job_input["destination"]
    print(["/kaniko/executor", "--context", context, "--dockerfile", dockerfile_path, "--destination", destination])
    subprocess.run(["/kaniko/executor", "--context={}".format(context), "--dockerfile={}".format(dockerfile_path), "--destination={}".format(destination)])

runpod.serverless.start({"handler": build_image})
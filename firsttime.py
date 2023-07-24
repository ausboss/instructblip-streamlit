import argparse
import glob
import re
import os
import site
import subprocess
import sys
import shutil
import multiprocessing
import stat

script_dir = os.getcwd()
conda_env_path = os.path.join(script_dir, "installer_files", "env")

# Use this to set your command-line flags. For the full list, see:
# https://github.com/oobabooga/text-generation-webui/#starting-the-web-ui
# Example: CMD_FLAGS = '--chat --listen'
CMD_FLAGS = '--chat'


# Allows users to set flags in "OOBABOOGA_FLAGS" environment variable
if "OOBABOOGA_FLAGS" in os.environ:
    CMD_FLAGS = os.environ["OOBABOOGA_FLAGS"]
    print("The following flags have been taken from the environment variable 'OOBABOOGA_FLAGS':")
    print(CMD_FLAGS)
    print("To use the CMD_FLAGS Inside webui.py, unset 'OOBABOOGA_FLAGS'.\n")


def print_big_message(message):
    message = message.strip()
    lines = message.split('\n')
    print("\n\n*******************************************************************")
    for line in lines:
        if line.strip() != '':
            print("*", line)

    print("*******************************************************************\n\n")


def run_cmd(cmd, assert_success=False, environment=False, capture_output=False, env=None):
    # Use the conda environment
    if environment:
        if sys.platform.startswith("win"):
            conda_bat_path = os.path.join(script_dir, "installer_files", "conda", "condabin", "conda.bat")
            cmd = "\"" + conda_bat_path + "\" activate \"" + conda_env_path + "\" >nul && " + cmd
        else:
            conda_sh_path = os.path.join(script_dir, "installer_files", "conda", "etc", "profile.d", "conda.sh")
            cmd = ". \"" + conda_sh_path + "\" && conda activate \"" + conda_env_path + "\" && " + cmd

    # Run shell commands
    result = subprocess.run(cmd, shell=True, capture_output=capture_output, env=env)

    # Assert the command ran successfully
    if assert_success and result.returncode != 0:
        print("Command '" + cmd + "' failed with exit status code '" + str(result.returncode) + "'. Exiting...")
        sys.exit()

    return result


def check_env():
    # If we have access to conda, we are probably in an environment
    conda_exist = run_cmd("conda", environment=True, capture_output=True).returncode == 0
    if not conda_exist:
        print("Conda is not installed. Exiting...")
        sys.exit()

    # Ensure this is a new environment and not the base environment
    if os.environ["CONDA_DEFAULT_ENV"] == "base":
        print("Create an environment for this project and activate it. Exiting...")
        sys.exit()


def install_dependencies():
    # Select your GPU or, choose to run in CPU mode
    print("What is your GPU")
    print()
    print("A) NVIDIA")
    print("B) AMD")
    print("C) Apple M Series")
    print("D) None (I want to run in CPU mode)")
    print()
    gpuchoice = input("Input> ").lower()

    if gpuchoice == "d":
        print_big_message("Once the installation ends, make sure to open webui.py with a text editor\nand add the --cpu flag to CMD_FLAGS.")

    # Install the version of PyTorch needed
    if gpuchoice == "a":
        run_cmd('conda install -y -k cuda ninja git -c nvidia/label/cuda-11.7.0 -c nvidia && python -m pip install torch==2.0.1+cu117 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu117', assert_success=True, environment=True)
    elif gpuchoice == "b":
        print("AMD GPUs are not supported. Exiting...")
        sys.exit()
    elif gpuchoice == "c":
        run_cmd("conda install -y -k ninja git && python -m pip install torch torchvision torchaudio", assert_success=True, environment=True)
    elif gpuchoice == "d":
        if sys.platform.startswith("linux"):
            run_cmd("conda install -y -k ninja git && python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu", assert_success=True, environment=True)
        else:
            run_cmd("conda install -y -k ninja git && python -m pip install torch torchvision torchaudio", assert_success=True, environment=True)

    else:
        print("Invalid choice. Exiting...")
        sys.exit()

    # Clone webui to our computer
    run_cmd("git clone https://github.com/oobabooga/text-generation-webui.git", assert_success=True, environment=True)

    # Install the webui dependencies
    update_dependencies()


def update_dependencies():
    os.chdir("text-generation-webui")
    run_cmd("git pull", assert_success=True, environment=True)

    # Workaround for git+ packages not updating properly  Also store requirements.txt for later use
    with open("requirements.txt") as f:
        textgen_requirements = f.read()
        git_requirements = [req for req in textgen_requirements.splitlines() if req.startswith("git+")]

    # Loop through each "git+" requirement and uninstall it
    for req in git_requirements:
        # Extract the package name from the "git+" requirement
        url = req.replace("git+", "")
        package_name = url.split("/")[-1].split("@")[0]

        # Uninstall the package using pip
        run_cmd("python -m pip uninstall -y " + package_name, environment=True)
        print(f"Uninstalled {package_name}")

    # Installs/Updates dependencies from all requirements.txt
    run_cmd("python -m pip install -r requirements.txt --upgrade", assert_success=True, environment=True)
    extensions = next(os.walk("extensions"))[1]
    for extension in extensions:
        if extension in ['superbooga']:  # No wheels available for dependencies
            continue

        extension_req_path = os.path.join("extensions", extension, "requirements.txt")
        if os.path.exists(extension_req_path):
            run_cmd("python -m pip install -r " + extension_req_path + " --upgrade", assert_success=True, environment=True)

    # The following dependencies are for CUDA, not CPU
    # Parse output of 'pip show torch' to determine torch version
    torver_cmd = run_cmd("python -m pip show torch", assert_success=True, environment=True, capture_output=True)
    torver = [v.split()[1] for v in torver_cmd.stdout.decode('utf-8').splitlines() if 'Version:' in v][0]

    # Check for '+cu' in version string to determine if torch uses CUDA or not   check for pytorch-cuda as well for backwards compatibility
    if '+cu' not in torver and run_cmd("conda list -f pytorch-cuda | grep pytorch-cuda", environment=True, capture_output=True).returncode == 1:
        return

    # Get GPU CUDA/compute support
    nvcc_device_query = "__nvcc_device_query" if not sys.platform.startswith("win") else "__nvcc_device_query.exe"
    compute_array = run_cmd(os.path.join(conda_env_path, "bin", nvcc_device_query), environment=True, capture_output=True)

    # Finds the path to your dependencies
    for sitedir in site.getsitepackages():
        if "site-packages" in sitedir:
            site_packages_path = sitedir
            break

    # This path is critical to installing the following dependencies
    if site_packages_path is None:
        print("Could not find the path to your Python packages. Exiting...")
        sys.exit()

    # Fix a bitsandbytes compatibility issue with Linux
    # if sys.platform.startswith("linux"):
    #     shutil.copy(os.path.join(site_packages_path, "bitsandbytes", "libbitsandbytes_cuda117.so"), os.path.join(site_packages_path, "bitsandbytes", "libbitsandbytes_cpu.so"))

    if not os.path.exists("repositories/"):
        os.mkdir("repositories")

    os.chdir("repositories")

    # Install or update exllama as needed
    if not os.path.exists("exllama/"):
        run_cmd("git clone https://github.com/turboderp/exllama.git", environment=True)
    else:
        os.chdir("exllama")
        run_cmd("git pull", environment=True)
        os.chdir("..")

    # Fix build issue with exllama in Linux/WSL
    if sys.platform.startswith("linux") and not os.path.exists(f"{conda_env_path}/lib64"):
        run_cmd(f'ln -s "{conda_env_path}/lib" "{conda_env_path}/lib64"', environment=True)

    # oobabooga fork requires min compute of 6.0
    gptq_min_compute = 60
    gptq_min_compute_check = any(int(compute) >= gptq_min_compute for compute in compute_array.stdout.decode('utf-8').split(',')) if compute_array.returncode == 0 else False

    # Install GPTQ-for-LLaMa which enables 4bit CUDA quantization
    if not os.path.exists("GPTQ-for-LLaMa/"):
        # Install oobabooga fork if min compute met or if failed to check
        if gptq_min_compute_check or compute_array.returncode != 0:
            run_cmd("git clone https://github.com/oobabooga/GPTQ-for-LLaMa.git -b cuda", assert_success=True, environment=True)
        else:
            run_cmd("git clone https://github.com/qwopqwop200/GPTQ-for-LLaMa.git -b cuda", assert_success=True, environment=True)

    # Install GPTQ-for-LLaMa dependencies
    os.chdir("GPTQ-for-LLaMa")
    run_cmd("git pull", assert_success=True, environment=True)

    # On some Linux distributions, g++ may not exist or be the wrong version to compile GPTQ-for-LLaMa
    if sys.platform.startswith("linux"):
        gxx_output = run_cmd("g++ -dumpfullversion -dumpversion", environment=True, capture_output=True)
        if gxx_output.returncode != 0 or int(gxx_output.stdout.strip().split(b".")[0]) > 11:
            # Install the correct version of g++
            run_cmd("conda install -y -k gxx_linux-64=11.2.0", environment=True)

    # Compile and install GPTQ-for-LLaMa
    if os.path.exists('setup_cuda.py'):
        os.rename("setup_cuda.py", "setup.py")

    build_gptq = run_cmd("python -m pip install .", environment=True).returncode == 0

    # Wheel installation can fail while in the build directory of a package with the same name
    os.chdir("..")

    # If the path does not exist, then the install failed
    quant_cuda_path_regex = os.path.join(site_packages_path, "quant_cuda*/")
    quant_cuda_path = glob.glob(quant_cuda_path_regex)
    if not build_gptq:
        # Attempt installation via alternative, Windows/Linux-specific method
        if (sys.platform.startswith("win") or sys.platform.startswith("linux")) and not quant_cuda_path:
            print_big_message("WARNING: GPTQ-for-LLaMa compilation failed, but this is FINE and can be ignored!\nThe installer will proceed to install a pre-compiled wheel.")
            wheel = f"{'' if gptq_min_compute_check or compute_array.returncode != 0 else '832e220d6dbf11bec5eaa8b221a52c1c854d2a25/'}quant_cuda-0.0.0-cp310-cp310-{'linux_x86_64' if sys.platform.startswith('linux') else 'win_amd64'}.whl"
            url = f"https://github.com/jllllll/GPTQ-for-LLaMa-Wheels/raw/{'Linux-x64' if sys.platform.startswith('linux') else 'main'}/" + wheel

            result = run_cmd("python -m pip install " + url, environment=True)
            if result.returncode == 0:
                print("Wheel installation success!")
            else:
                print("ERROR: GPTQ wheel installation failed. You will not be able to use GPTQ-based models.")
        elif quant_cuda_path:
            print_big_message("WARNING: GPTQ-for-LLaMa compilation failed, but this is FINE and can be ignored!\nquant_cuda has already been installed.")
        else:
            print("ERROR: GPTQ CUDA kernel compilation failed.")
            print("You will not be able to use GPTQ-based models.")

        print("Continuing with install..")


def download_model():
    os.chdir("text-generation-webui")
    run_cmd("python download-model.py", environment=True)



def remove_readonly(func, path, _):
    "Clear the readonly bit and reattempt the removal"
    os.chmod(path, stat.S_IWRITE)
    func(path)

def launch_webui():
    run_cmd(f"pip install -q -r requirements.txt", environment=True)
    directory = "text-generation-webui"
    shutil.rmtree(directory, onerror=remove_readonly)
    print(f"'{directory}' has been deleted.")
    
    # Start imageserver.py in a separate process
    p1 = multiprocessing.Process(target=run_cmd, args=("python imageserver.py", True))
    p1.start()

    # Start Streamlit in another process
    p2 = multiprocessing.Process(target=run_cmd, args=("streamlit run chatoverimage.py", True))
    p2.start()

    





if __name__ == "__main__":
    # Verifies we are in a conda environment
    check_env()

    parser = argparse.ArgumentParser()
    parser.add_argument('--update', action='store_true', help='Update the web UI.')
    args = parser.parse_args()

    if args.update:
        update_dependencies()
    else:
        # If webui has already been installed, skip and run
        if not os.path.exists("text-generation-webui/"):
            install_dependencies()
            os.chdir(script_dir)

        # # Check if a model has been downloaded yet
        # if len([item for item in glob.glob('text-generation-webui/models/*') if not item.endswith(('.txt', '.yaml'))]) == 0:
        #     print_big_message("WARNING: You haven't downloaded any model yet.\nOnce the web UI launches, head over to the bottom of the \"Model\" tab and download one.")

        # # Workaround for llama-cpp-python loading paths in CUDA env vars even if they do not exist
        # conda_path_bin = os.path.join(conda_env_path, "bin")
        # if not os.path.exists(conda_path_bin):
        #     os.mkdir(conda_path_bin)

        # Launch the webui
        launch_webui()

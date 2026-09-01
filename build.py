import os
import sys
import json
import subprocess
import glob

def clone_repo(repo_url, branch, path):
    """Clone a git repository if it doesn't exist."""
    if not os.path.exists(path):
        print(f"Cloning {repo_url} (branch: {branch}) into {path}...")
        subprocess.check_call(["git", "clone", "-b", branch, "--depth", "1", repo_url, path])
    else:
        print(f"Repository {path} already exists. Pulling latest changes...")
        subprocess.check_call(["git", "-C", path, "pull"])

def setup_toolchain(toolchains):
    """Setup toolchain paths for cross-compilation."""
    toolchain_paths = []
    for tc in toolchains:
        if "repo" in tc:
            repo_url = tc["repo"]
            branch = tc.get("branch", "master")
            name = tc["name"]
            # Clone toolchain
            tc_dir = f"toolchains/{name}"
            clone_repo(repo_url, branch, tc_dir)
            # Find bin directory
            bin_dirs = glob.glob(f"{tc_dir}/bin")
            for bin_dir in bin_dirs:
                if os.path.exists(bin_dir):
                    toolchain_paths.append(bin_dir)
    return toolchain_paths

def build_kernel(config_file):
    """Main build function based on JSON config."""
    with open(config_file, 'r') as f:
        configs = json.load(f)

    for config in configs:
        kernel_source = config.get("kernelSource")
        if not kernel_source:
            continue

        repo = kernel_source.get("repo")
        branch = kernel_source.get("branch")
        device = kernel_source.get("device")
        defconfig = kernel_source.get("defconfig")
        params = config.get("params", {})
        toolchains = config.get("toolchains", [])
        
        arch = params.get("ARCH", "arm")
        cross_compile = params.get("CROSS_COMPILE", "arm-eabi-")
        cc = params.get("CC", "gcc")

        # Setup toolchains
        toolchain_paths = setup_toolchain(toolchains)
        
        # Clone the kernel source
        kernel_dir = f"kernel/{device}"
        clone_repo(repo, branch, kernel_dir)

        # Set up environment variables with toolchain paths
        env = os.environ.copy()
        env["ARCH"] = arch
        env["CROSS_COMPILE"] = cross_compile
        env["CC"] = cc
        
        # Add toolchain paths to PATH
        if toolchain_paths:
            path_env = env.get("PATH", "")
            for tc_path in toolchain_paths:
                if tc_path not in path_env:
                    path_env = f"{tc_path}:{path_env}"
            env["PATH"] = path_env

        # Build the kernel
        os.chdir(kernel_dir)
        print(f"Building kernel for {device} with defconfig {defconfig}...")
        print(f"Using PATH: {env['PATH']}")
        
        # Make defconfig
        subprocess.check_call(["make", defconfig], env=env)
        
        # Build the kernel (use 4 parallel jobs)
        subprocess.check_call(["make", "-j4"], env=env)
        
        # Go back to root
        os.chdir("../..")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build.py <config_file.json>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    if not os.path.exists(config_file):
        print(f"Config file {config_file} not found!")
        sys.exit(1)
    
    build_kernel(config_file)
    print("Build completed successfully!")

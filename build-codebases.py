import pandas as pd
import sys
from rich import print
import os
import shutil
import subprocess

def copy_and_build(csv_file, destination_path):
    df = pd.read_csv(csv_file, header=None)
    df.columns = ['project','test-flag'] 
    curr_dir = os.getcwd()
    for index, row in df.iterrows():
        url = row['project']
        flag = row['test-flag']
        project = url.split('/')[-1]
        print(f"I'm going to build project {project} in WebAssembly")
        # define the source and destination directories
        source_dir = os.path.join('./codebases', project)
        dest_dir = os.path.join(destination_path, project)
        if os.path.exists(dest_dir):
            print(f"Project {project} exists!")
            continue
        # copy the directory from source to destination
        if os.path.exists(source_dir):
            shutil.copytree(source_dir, dest_dir)
            print(f"Project {project} copied to {dest_dir}.")
        else:
            print(f"Source directory for {project} does not exist.")
            try: # clone the repository of the given url
                clone_command = f"git clone --recursive {url} {dest_dir}"
                subprocess.run(clone_command, shell=True, check=True,
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                print("Cloning is done!")
            except subprocess.CalledProcessError as error: continue

        # create a build diriectory and change to it
        build_dir = os.path.join(dest_dir, 'build')
        os.makedirs(build_dir, exist_ok=True)
        os.chdir(build_dir)
        c_compiler = "-DCMAKE_C_COMPILER="
        cpp_compiler = "-DCMAKE_CXX_COMPILER="

        if compiler == "gcc":
            c_compiler = c_compiler + "/usr/bin/gcc"
            cpp_compiler = cpp_compiler + "/usr/bin/g++"
        if compiler == "clang":
            c_compiler = c_compiler + "/usr/bin/clang"
            cpp_compiler = cpp_compiler + "/usr/bin/clang++"
        error = False
        testing = f"-D{flag}=ON"
        if compiler == "gcc" or compiler == "clang":
            config_command = ['cmake', testing, c_compiler, cpp_compiler, '..']
            build_command = ['cmake', '--build', '.', '-j']
        if compiler == "emcc":
            config_command = ['emcmake', 'cmake', testing, '..']
            build_command = ['emmake', 'cmake', '--build', '.', '-j']
        try: # configure the project using emcmake cmake
            subprocess.run(config_command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Configuration of {project} completed.")
        except subprocess.CalledProcessError as e:
            error = True
            print(f"Configuration failed for {project}: {e}")
        try: # build the project
            subprocess.run(build_command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Build completed for {project}.")
        except subprocess.CalledProcessError as e:
            error = True
            print(f"Build failed for {project}: {e}")
        if error: 
            print(f"[bold red]Building project {project} in WebAssembly failed![/bold red]")
        else:
            print(f"[bold green]Building project {project} in WebAssembly is done![/bold green]")
        os.chdir(curr_dir)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 build-codebases.py clang/gcc/emcc")
        sys.exit(1)
    compiler = sys.argv[1]
    if compiler != "clang" and compiler == "gcc" and compiler == "emcc":
        print("[bold red]Unknown Compiler![/bold red]")
        exit(0)
    csv_file_path = 'codebases.csv'
    destination_path = compiler + '-builds'  # define your destination path here
    copy_and_build(csv_file_path, destination_path)

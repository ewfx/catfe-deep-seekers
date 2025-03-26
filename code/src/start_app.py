#!/usr/bin/env python
"""
Start the Spring Boot application for testing.

This script helps to start the Spring Boot application from the cloned repository
for the purpose of testing the BDD test cases.
"""

import os
import sys
import json
import logging
import subprocess
import argparse
import time
import signal
import atexit

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants
CONFIG_FILE = "config.json"

def load_config():
    """Load configuration from config.json."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def find_app_jar(clone_dir):
    """Find the Spring Boot application JAR file."""
    logging.info(f"Looking for Spring Boot JAR in {clone_dir}")
    
    # Check if Java is installed first
    java_path = check_java_installation()
    if not java_path:
        logging.error("Java is not installed or not found. Cannot build or run Spring Boot application.")
        return None
    
    # Set environment with JAVA_HOME if possible
    java_home = None
    if java_path != "java":
        if os.path.isfile(java_path):
            # Remove 'bin/java' or 'bin/java.exe' to get JAVA_HOME
            if java_path.endswith("java.exe"):
                java_home = os.path.dirname(os.path.dirname(java_path))
            else:
                java_home = os.path.dirname(os.path.dirname(java_path))
    
    env = os.environ.copy()
    if java_home:
        env["JAVA_HOME"] = java_home
        logging.info(f"Setting JAVA_HOME={java_home}")
    
    # Check if there's a target directory with JAR files
    target_dir = os.path.join(clone_dir, "target")
    if os.path.exists(target_dir):
        for file in os.listdir(target_dir):
            if file.endswith(".jar") and not file.endswith("-sources.jar") and not file.endswith("-javadoc.jar"):
                logging.info(f"Found JAR: {file}")
                return os.path.join(target_dir, file)
    
    # Check for gradle build
    build_dir = os.path.join(clone_dir, "build", "libs")
    if os.path.exists(build_dir):
        for file in os.listdir(build_dir):
            if file.endswith(".jar") and not file.endswith("-sources.jar") and not file.endswith("-javadoc.jar"):
                logging.info(f"Found JAR: {file}")
                return os.path.join(build_dir, file)
    
    # If nothing found, look for a build script
    mvnw_path = os.path.join(clone_dir, "mvnw")
    mvnw_cmd_path = os.path.join(clone_dir, "mvnw.cmd")
    if os.path.exists(mvnw_path) or os.path.exists(mvnw_cmd_path):
        logging.info("Maven wrapper found. Building project...")
        try:
            # Use different command format based on OS
            if sys.platform.startswith('win'):
                if os.path.exists(mvnw_cmd_path):
                    # On Windows, we need to use the full absolute path with proper backslashes
                    mvnw_cmd = [os.path.normpath(os.path.abspath(mvnw_cmd_path))]
                    logging.info(f"Using Maven wrapper at: {mvnw_cmd[0]}")
                else:
                    logging.warning("Maven wrapper cmd file not found. Trying alternative approach.")
                    # On Windows without mvnw.cmd, try direct call to Maven
                    maven_path = os.path.join(os.environ.get("MAVEN_HOME", ""), "bin", "mvn.cmd") 
                    if os.path.exists(maven_path):
                        mvnw_cmd = [maven_path]
                    else:
                        mvnw_cmd = ["mvn"]
            else:
                mvnw_cmd = ["./mvnw"]
                # Make sure mvnw is executable on Unix
                if os.path.exists(mvnw_path):
                    os.chmod(mvnw_path, os.stat(mvnw_path).st_mode | 0o111)
            
            logging.info(f"Executing Maven build with command: {' '.join(mvnw_cmd)}")
            build_result = subprocess.run(
                mvnw_cmd + ["clean", "package", "-DskipTests"],
                cwd=clone_dir,
                check=False,  # Changed to not raise exception
                capture_output=True,
                text=True,
                env=env
            )
            
            if build_result.returncode != 0:
                logging.error(f"Maven build failed with code {build_result.returncode}")
                logging.error(f"STDOUT: {build_result.stdout}")
                logging.error(f"STDERR: {build_result.stderr}")
                
                # Try with system Maven as a fallback
                logging.info("Trying with system Maven as fallback...")
                fallback_result = subprocess.run(
                    ["mvn", "clean", "package", "-DskipTests"],
                    cwd=clone_dir,
                    check=False,
                    capture_output=True,
                    text=True,
                    env=env
                )
                
                if fallback_result.returncode != 0:
                    logging.error("Maven fallback build also failed.")
                    return None
            
            # Try again to find JAR
            return find_app_jar(clone_dir)
        except Exception as e:
            logging.error(f"Failed to build with Maven: {e}")
            return None
    
    gradlew_path = os.path.join(clone_dir, "gradlew")
    gradlew_bat_path = os.path.join(clone_dir, "gradlew.bat")
    if os.path.exists(gradlew_path) or os.path.exists(gradlew_bat_path):
        logging.info("Gradle wrapper found. Building project...")
        try:
            # Use different command format based on OS
            if sys.platform.startswith('win'):
                if os.path.exists(gradlew_bat_path):
                    # Fix the path for Windows - use full path with proper backslashes
                    gradlew_cmd = [os.path.normpath(os.path.abspath(gradlew_bat_path))]
                    logging.info(f"Using Gradle wrapper at: {gradlew_cmd[0]}")
                else:
                    logging.warning("Gradle wrapper bat file not found. Trying alternative approach.")
                    # On Windows without gradlew.bat, try direct call to Gradle
                    gradle_path = os.path.join(os.environ.get("GRADLE_HOME", ""), "bin", "gradle.bat")
                    if os.path.exists(gradle_path):
                        gradlew_cmd = [gradle_path]
                    else:
                        gradlew_cmd = ["gradle"]
            else:
                gradlew_cmd = ["./gradlew"]
                # Make sure gradlew is executable on Unix
                if os.path.exists(gradlew_path):
                    os.chmod(gradlew_path, os.stat(gradlew_path).st_mode | 0o111)
            
            logging.info(f"Executing Gradle build with command: {' '.join(gradlew_cmd)}")
            build_result = subprocess.run(
                gradlew_cmd + ["build", "-x", "test"],
                cwd=clone_dir,
                check=False,  # Changed to not raise exception
                capture_output=True,
                text=True,
                env=env
            )
            
            if build_result.returncode != 0:
                logging.error(f"Gradle build failed with code {build_result.returncode}")
                logging.error(f"STDOUT: {build_result.stdout}")
                logging.error(f"STDERR: {build_result.stderr}")
                
                # Try with system Gradle as a fallback
                logging.info("Trying with system Gradle as fallback...")
                fallback_result = subprocess.run(
                    ["gradle", "build", "-x", "test"],
                    cwd=clone_dir,
                    check=False,
                    capture_output=True,
                    text=True,
                    env=env
                )
                
                if fallback_result.returncode != 0:
                    logging.error("Gradle fallback build also failed.")
                    return None
            
            # Try again to find JAR
            return find_app_jar(clone_dir)
        except Exception as e:
            logging.error(f"Failed to build with Gradle: {e}")
            return None
    
    logging.error("Could not find or build JAR file.")
    return None

def check_java_installation():
    """Check if Java is installed and return version."""
    # Common Java installation paths
    java_paths = []
    
    if sys.platform.startswith('win'):
        # Windows specific paths
        java_paths = [
            "java",  # Check PATH first
            r"C:\Program Files\Java\jdk-17\bin\java.exe",  # Fixed Windows path with raw string
            r"C:\Program Files\Common Files\Oracle\Java\javapath\java.exe",  # Fixed Windows path
            os.path.join("C:\\", "Program Files", "Java", "jdk-17", "bin", "java.exe"),  # Alternative with escaped backslashes
            os.path.join("C:\\", "Program Files", "Common Files", "Oracle", "Java", "javapath", "java.exe"),
            os.path.join("C:\\", "Program Files", "Java", "jdk*", "bin", "java.exe"),
            os.path.join("C:\\", "Program Files (x86)", "Java", "jdk*", "bin", "java.exe"),
            os.path.join("C:\\", "Program Files", "Eclipse Adoptium", "jdk*", "bin", "java.exe")
        ]
    else:
        # Linux/Mac specific paths
        java_paths = [
            "java",  # Check PATH first
            "/usr/bin/java",
            "/usr/local/bin/java",
            "/opt/jdk*/bin/java"
        ]
    
    # Try each possible Java path
    for java_path in java_paths:
        if "*" in java_path:
            # Handle wildcard paths - find the most recent matching version
            try:
                base_dir = os.path.dirname(java_path.replace("*", ""))
                if os.path.exists(base_dir):
                    matching_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
                    # Sort to find the most recent version
                    matching_dirs.sort(reverse=True)
                    for d in matching_dirs:
                        full_path = os.path.join(base_dir, d, "java" if "bin" in base_dir else "bin", "java")
                        if os.path.exists(full_path):
                            if sys.platform.startswith('win'):
                                full_path += ".exe"
                            if os.path.exists(full_path):
                                java_path = full_path
                                break
            except Exception as e:
                logging.warning(f"Error checking wildcard path {java_path}: {e}")
                continue
        
        try:
            path_to_check = java_path if "*" not in java_path else None
            if not path_to_check:
                continue
                
            if not os.path.exists(path_to_check) and path_to_check != "java":
                logging.warning(f"Java path not found: {path_to_check}")
                continue
                
            logging.info(f"Trying Java path: {path_to_check}")
            result = subprocess.run(
                [path_to_check, "-version"],
                check=False,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Java version info is typically in stderr
                version_output = result.stderr if result.stderr else result.stdout
                logging.info(f"Java is installed: {version_output.splitlines()[0]}")
                return path_to_check  # Return the working java path
            else:
                logging.warning(f"Java check failed for {path_to_check} with non-zero exit code")
        except Exception as e:
            logging.warning(f"Error checking Java at {path_to_check}: {e}")
    
    logging.error("Java is not installed or not in PATH. Cannot run Spring Boot application.")
    return None

def find_java_files(clone_dir):
    """Find all Java files with main methods."""
    logging.info(f"Looking for Java files with main methods in {clone_dir}")
    main_java_files = []
    
    try:
        for root, _, files in os.walk(clone_dir):
            # Skip test directories
            if 'test' in root.lower():
                continue
                
            for file in files:
                if file.endswith('.java'):
                    file_path = os.path.join(root, file)
                    
                    # Check if file contains a main method
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'public static void main(String[] args)' in content and 'SpringApplication.run' in content:
                                main_java_files.append(file_path)
                                logging.info(f"Found Spring Boot main class: {file_path}")
                    except Exception as e:
                        logging.warning(f"Error reading file {file_path}: {e}")
    except Exception as e:
        logging.error(f"Error searching for Java files: {e}")
    
    return main_java_files

def run_spring_boot_directly(clone_dir, port, profile=None):
    """Run Spring Boot application directly using Java."""
    logging.info("Attempting to run Spring Boot application directly...")
    
    # Check if Java is installed
    java_path = check_java_installation()
    if not java_path:
        return None
    
    # Find main class file
    main_files = find_java_files(clone_dir)
    if not main_files:
        logging.error("Could not find Spring Boot main class.")
        return None
    
    # Use the first found main class
    main_file = main_files[0]
    
    try:
        # Get javac path from java path
        if java_path == "java":
            javac_path = "javac"
        elif java_path.endswith("java.exe"):
            javac_path = java_path.replace("java.exe", "javac.exe")
        else:
            javac_path = java_path.replace("java", "javac")
        
        logging.info(f"Using javac at: {javac_path}")
        
        # Compile the application
        logging.info("Compiling Spring Boot application...")
        compile_result = subprocess.run(
            [javac_path, main_file],
            cwd=clone_dir,
            check=False,
            capture_output=True,
            text=True
        )
        
        if compile_result.returncode != 0:
            logging.error(f"Compilation failed: {compile_result.stderr}")
            return None
        
        # Get the classpath
        classpath = os.path.dirname(main_file)
        
        # Get the main class name
        relative_path = os.path.relpath(main_file, clone_dir)
        if relative_path.startswith('src/main/java/'):
            main_class = relative_path[14:].replace('.java', '').replace(os.path.sep, '.')
        else:
            main_class = os.path.basename(main_file).replace('.java', '')
        
        # Run the application
        cmd = [
            java_path, 
            "-cp", classpath,
            main_class,
            f"--server.port={port}"
        ]
        
        if profile:
            cmd.append(f"--spring.profiles.active={profile}")
        
        logging.info(f"Running Spring Boot application with command: {cmd}")
        process = subprocess.Popen(
            cmd,
            cwd=clone_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return process
    except Exception as e:
        logging.error(f"Error running Spring Boot directly: {e}")
        return None

def start_app(jar_path, port, profile=None):
    """Start the Spring Boot application."""
    logging.info(f"Starting Spring Boot application on port {port}")
    
    # Check if Java is installed
    java_path = check_java_installation()
    if not java_path:
        return None
    
    # Make sure the JAR path exists
    if not os.path.exists(jar_path):
        logging.error(f"JAR file not found: {jar_path}")
        return None
    
    logging.info(f"Using Java at: {java_path} to run: {jar_path}")
    
    # Build command
    cmd = [java_path, "-jar", jar_path, f"--server.port={port}"]
    
    # Add profile if specified
    if profile:
        cmd.append(f"--spring.profiles.active={profile}")
    
    # Start the process
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Register cleanup function
        def cleanup():
            if process.poll() is None:
                logging.info("Stopping Spring Boot application...")
                process.terminate()
                process.wait(timeout=5)
                if process.poll() is None:
                    process.kill()
        
        atexit.register(cleanup)
        signal.signal(signal.SIGINT, lambda sig, frame: (cleanup(), sys.exit(0)))
        signal.signal(signal.SIGTERM, lambda sig, frame: (cleanup(), sys.exit(0)))
        
        # Wait for app to start
        logging.info("Waiting for application to start...")
        ready = False
        timeout = 60  # 60 seconds
        start_time = time.time()
        
        while not ready and time.time() - start_time < timeout:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logging.error("Application failed to start")
                logging.error(f"STDOUT: {stdout}")
                logging.error(f"STDERR: {stderr}")
                return None
            
            line = process.stdout.readline()
            if "Started " in line and "in" in line and "seconds" in line:
                ready = True
                logging.info("Application started successfully")
            elif line:
                print(line.strip())
            
            time.sleep(0.1)
        
        if not ready:
            logging.warning("Application might not have started properly")
        
        return process
    except Exception as e:
        logging.error(f"Error starting application: {e}")
        return None

def check_docker_installation():
    """Check if Docker is installed."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            check=False,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logging.info(f"Docker is installed: {result.stdout.strip()}")
            return True
        else:
            logging.warning("Docker check failed with non-zero exit code")
    except Exception as e:
        logging.warning(f"Error checking Docker: {e}")
    
    logging.warning("Docker is not installed or not in PATH")
    return False

def run_with_docker(clone_dir, port, profile=None):
    """Run the application using Docker."""
    logging.info("Attempting to run application with Docker...")
    
    # Check if Docker is installed
    if not check_docker_installation():
        logging.error("Docker is not installed. Cannot run application with Docker.")
        return None
    
    # Check if Dockerfile exists
    dockerfile_path = os.path.join(clone_dir, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        logging.warning("Dockerfile not found in the repository.")
        docker_compose_path = os.path.join(clone_dir, "docker-compose.yml")
        if os.path.exists(docker_compose_path):
            logging.info("Found docker-compose.yml, will use that instead.")
            return run_with_docker_compose(clone_dir, port, profile)
        else:
            logging.error("No Docker configuration found in the repository.")
            return None
    
    # Check Dockerfile content
    with open(dockerfile_path, 'r', encoding='utf-8') as f:
        dockerfile_content = f.read()
        
    # If Dockerfile copies from target directory, build the JAR first
    if 'target/' in dockerfile_content or '.jar' in dockerfile_content:
        logging.info("Dockerfile references JAR files. Building the JAR first...")
        
        # Check if target directory with JAR exists
        target_dir = os.path.join(clone_dir, "target")
        jar_exists = False
        
        if os.path.exists(target_dir):
            for file in os.listdir(target_dir):
                if file.endswith(".jar") and not file.endswith("-sources.jar") and not file.endswith("-javadoc.jar"):
                    jar_exists = True
                    logging.info(f"Found existing JAR: {file}")
                    break
        
        # If JAR doesn't exist, build it
        if not jar_exists:
            logging.info("Building JAR using Maven or Gradle...")
            # Try to build the JAR using the find_app_jar function
            jar_path = find_app_jar(clone_dir)
            if not jar_path:
                logging.error("Failed to build JAR required by Docker. Cannot proceed.")
                return None
    
    # Build Docker image
    image_name = "spring-boot-app:latest"
    logging.info(f"Building Docker image {image_name}...")
    
    try:
        # Build the Docker image
        build_result = subprocess.run(
            ["docker", "build", "-t", image_name, "."],
            cwd=clone_dir,
            check=False,
            capture_output=True,
            text=True
        )
        
        if build_result.returncode != 0:
            logging.error(f"Failed to build Docker image: {build_result.stderr}")
            return None
        
        logging.info("Docker image built successfully")
        
        # Run the Docker container
        container_name = "spring-boot-app-container"
        
        # Stop and remove existing container if it exists
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            check=False,
            capture_output=True
        )
        
        # Build run command
        run_cmd = [
            "docker", "run",
            "--name", container_name,
            "-p", f"{port}:8080",
            "-d"  # Run in detached mode
        ]
        
        # Add environment variables for profile if needed
        if profile:
            run_cmd.extend(["-e", f"SPRING_PROFILES_ACTIVE={profile}"])
            
        run_cmd.append(image_name)
        
        logging.info(f"Running Docker container with command: {' '.join(run_cmd)}")
        run_result = subprocess.run(
            run_cmd,
            check=False,
            capture_output=True,
            text=True
        )
        
        if run_result.returncode != 0:
            logging.error(f"Failed to run Docker container: {run_result.stderr}")
            return None
        
        container_id = run_result.stdout.strip()
        logging.info(f"Docker container started with ID: {container_id}")
        
        # Wait for application to start
        logging.info("Waiting for Docker container to start the application...")
        time.sleep(5)  # Initial wait for container to initialize
        
        # Check logs to see if application started
        logs_cmd = ["docker", "logs", container_id]
        timeout = 60
        start_time = time.time()
        ready = False
        
        while not ready and time.time() - start_time < timeout:
            logs_result = subprocess.run(
                logs_cmd,
                check=False,
                capture_output=True,
                text=True
            )
            
            logs = logs_result.stdout
            
            if "Started " in logs and "in" in logs and "seconds" in logs:
                ready = True
                logging.info("Application started successfully in Docker container")
            else:
                time.sleep(1)
        
        if not ready:
            logging.warning("Could not confirm if application started properly in Docker")
        
        # Create a dummy process-like object to match the expected return type
        class DockerProcess:
            def __init__(self, container_id):
                self.container_id = container_id
                self.stdout = DockerLogs(container_id, "stdout")
                self.stderr = DockerLogs(container_id, "stderr")
            
            def poll(self):
                # Check if container is still running
                result = subprocess.run(
                    ["docker", "inspect", "-f", "{{.State.Running}}", self.container_id],
                    check=False,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0 or result.stdout.strip() != "true":
                    return 1
                return None
            
            def terminate(self):
                subprocess.run(
                    ["docker", "stop", self.container_id],
                    check=False,
                    capture_output=True
                )
            
            def kill(self):
                subprocess.run(
                    ["docker", "rm", "-f", self.container_id],
                    check=False,
                    capture_output=True
                )
            
            def wait(self, timeout=None):
                try:
                    subprocess.run(
                        ["docker", "wait", self.container_id],
                        check=False,
                        timeout=timeout
                    )
                except subprocess.TimeoutExpired:
                    pass
        
        class DockerLogs:
            def __init__(self, container_id, stream_type):
                self.container_id = container_id
                self.stream_type = stream_type
                self.pos = 0
            
            def readline(self):
                # Get logs from the container
                stream_option = "--stderr" if self.stream_type == "stderr" else "--stdout"
                result = subprocess.run(
                    ["docker", "logs", stream_option, "--tail", "10", self.container_id],
                    check=False,
                    capture_output=True,
                    text=True
                )
                lines = result.stdout.splitlines()
                if lines:
                    # Just return the last line for simplicity
                    return lines[-1] + "\n"
                return ""
        
        return DockerProcess(container_id)
    
    except Exception as e:
        logging.error(f"Error running with Docker: {e}")
        return None

def run_with_docker_compose(clone_dir, port, profile=None):
    """Run the application using Docker Compose."""
    logging.info("Attempting to run application with Docker Compose...")
    
    # Check if Docker Compose file exists
    compose_file = os.path.join(clone_dir, "docker-compose.yml")
    if not os.path.exists(compose_file):
        logging.error("docker-compose.yml not found in the repository.")
        return None
    
    try:
        # Build and run with Docker Compose
        env = os.environ.copy()
        if profile:
            env["SPRING_PROFILES_ACTIVE"] = profile
        
        # Set port explicitly if possible
        env["PORT"] = str(port)
        
        # Stop any running containers (if any)
        subprocess.run(
            ["docker-compose", "down"],
            cwd=clone_dir,
            check=False,
            capture_output=True,
            text=True
        )
        
        # Start with Docker Compose
        compose_up = subprocess.run(
            ["docker-compose", "up", "-d", "--build"],
            cwd=clone_dir,
            check=False,
            capture_output=True,
            text=True,
            env=env
        )
        
        if compose_up.returncode != 0:
            logging.error(f"Failed to start with Docker Compose: {compose_up.stderr}")
            return None
        
        logging.info("Application started with Docker Compose")
        
        # Create a dummy process object similar to the one for Docker
        class DockerComposeProcess:
            def __init__(self, clone_dir):
                self.clone_dir = clone_dir
                self.stdout = DockerComposeLogs(clone_dir, "stdout")
                self.stderr = DockerComposeLogs(clone_dir, "stderr")
            
            def poll(self):
                # Check if containers are still running
                result = subprocess.run(
                    ["docker-compose", "ps", "-q"],
                    cwd=self.clone_dir,
                    check=False,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0 or not result.stdout.strip():
                    return 1
                return None
            
            def terminate(self):
                subprocess.run(
                    ["docker-compose", "stop"],
                    cwd=self.clone_dir,
                    check=False,
                    capture_output=True
                )
            
            def kill(self):
                subprocess.run(
                    ["docker-compose", "down"],
                    cwd=self.clone_dir,
                    check=False,
                    capture_output=True
                )
            
            def wait(self, timeout=None):
                # This is a simplified wait implementation
                try:
                    time.sleep(timeout if timeout else 3600)
                except KeyboardInterrupt:
                    pass
        
        class DockerComposeLogs:
            def __init__(self, clone_dir, stream_type):
                self.clone_dir = clone_dir
                self.stream_type = stream_type
            
            def readline(self):
                # Get logs from docker-compose
                result = subprocess.run(
                    ["docker-compose", "logs", "--tail=10"],
                    cwd=self.clone_dir,
                    check=False,
                    capture_output=True,
                    text=True
                )
                lines = result.stdout.splitlines()
                if lines:
                    return lines[-1] + "\n"
                return ""
        
        # Wait to see if application started
        logging.info("Waiting for application to start in Docker Compose...")
        time.sleep(10)  # Initial wait for containers
        
        return DockerComposeProcess(clone_dir)
    
    except Exception as e:
        logging.error(f"Error running with Docker Compose: {e}")
        return None

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Start Spring Boot application for testing")
    parser.add_argument("--port", type=int, default=8080, help="Port to run the application on")
    parser.add_argument("--profile", help="Spring profile to activate")
    parser.add_argument("--jar", help="Path to JAR file (optional)")
    parser.add_argument("--direct", action="store_true", help="Try to run Spring Boot directly without building JAR")
    parser.add_argument("--docker", action="store_true", help="Try to run application with Docker if available")
    parser.add_argument("--debug", action="store_true", help="Print verbose debugging information")
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load config
    config = load_config()
    clone_dir = config.get("clone_dir", "./gleanclone")
    clone_dir = os.path.abspath(clone_dir)  # Make sure we have an absolute path
    
    logging.info(f"Using clone directory: {clone_dir}")
    
    # Find JAR file
    jar_path = args.jar
    process = None
    
    # Try Docker if flag is set or Dockerfile/docker-compose.yml exists
    if args.docker or (
        os.path.exists(os.path.join(clone_dir, "Dockerfile")) or 
        os.path.exists(os.path.join(clone_dir, "docker-compose.yml"))
    ):
        logging.info("Docker configuration detected, trying Docker first...")
        process = run_with_docker(clone_dir, args.port, args.profile)
    
    # Try direct Java execution if no process yet and direct flag is set
    if not process and args.direct:
        process = run_spring_boot_directly(clone_dir, args.port, args.profile)
    
    # Find and use JAR file if no process yet
    if not process and not jar_path:
        jar_path = find_app_jar(clone_dir)
    
    if not process and jar_path:
        process = start_app(jar_path, args.port, args.profile)
    
    if not process:
        logging.error("Could not start application with any method.")
        return 1
    
    # Update config with API URL
    config["api_base_url"] = f"http://localhost:{args.port}"
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    logging.info(f"Updated API base URL in {CONFIG_FILE}")
    
    logging.info(f"Application running on port {args.port}")
    logging.info("Press Ctrl+C to stop")
    
    # Keep running until interrupted
    try:
        process.wait()
    except KeyboardInterrupt:
        pass
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
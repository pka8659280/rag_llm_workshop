# Docker Installation & Run Guideline

## 1. Prerequisites

- Windows 10/11 Pro, Enterprise, or Education (64-bit) with virtualization enabled in BIOS. Windows Home users need WSL2 backend setup.
- Download Docker Desktop from: <https://www.docker.com/products/docker-desktop/>

## 2. Install Docker Desktop

- Run the downloaded installer and follow the on-screen steps.
- After installation, restart your computer if prompted.
- Launch Docker Desktop from the Start menu.
- Wait until the Docker engine status shows "Running" (whale icon in the system tray turns steady).

## 3. Verify Installation

- Open PowerShell or Command Prompt and run:

```powershell
docker --version
docker info
```

- If the commands return version/configuration details, Docker is ready.

## 4. Pull an Image (Example)

- Pull an image from Docker Hub:

```powershell
docker pull hello-world
```

## 5. Run a Container

- Run a container from the pulled image:

```powershell
docker run hello-world
```

- If you see the "Hello from Docker!" message, Docker is working correctly.

## 6. Basic Docker Commands

| Description                      | Command                                              |
| -------------------------------- | ---------------------------------------------------- |
| List running containers          | `docker ps`                                          |
| List all containers              | `docker ps -a`                                       |
| List local images                | `docker images`                                      |
| Stop a container                 | `docker stop <container_name>`                       |
| Start a stopped container        | `docker start <container_name>`                      |
| Remove a container               | `docker rm <container_name>`                         |
| View container logs              | `docker logs <container_name>`                       |
| Run a container in background    | `docker run -d <image_name>`                         |
| Run a container with name        | `docker run --name <name> <image_name>`              |
| Map a container port to host     | `docker run -p <host_port>:<container_port> <image_name>` |
| Mount a host directory as volume | `docker run -v <host_dir>:<container_dir> <image_name>` |

## 7. Tips

- Use `-d` to run containers in the background.
- Use `--name` to give containers meaningful names for easier management.
- Use `-v` to persist data across container restarts.
- Use `-p` to expose container ports to the host.

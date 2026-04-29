# Docker build and AWS deploy notes

Quick steps to build and run the Docker image locally:

- Build the image:

```
docker build -t finance-triage:latest .
```

- Run the container (default uses `app.py`; change to `main.py` if needed):

```
docker run -d --name finance-triage -p 8080:8080 finance-triage:latest
```

Bind container to a specific host IP (AWS EC2 public IP):

- If your EC2 instance has public IP `A.B.C.D` and you want to expose container port `8080` on host port `80`, run:

```
docker run -d --name finance-triage -p A.B.C.D:80:8080 finance-triage:latest
```

Notes for AWS deployment:

- Launch an EC2 instance and install Docker on it.
- In the EC2 Security Group, open the host port you published (for example, `80` or `8080`) to your desired sources (e.g., 0.0.0.0/0 for public).
- Use the EC2 public IP (or Elastic IP) in the `-p` mapping above to bind to that IP.
- Alternatively, run the container publishing only the host port (no IP) and rely on the instance's networking:

```
docker run -d --name finance-triage -p 80:8080 finance-triage:latest
```

- If your app listens on a different port, update `EXPOSE` in the `Dockerfile` and the `-p` mapping accordingly.
- To keep the container running after reboots, add `--restart unless-stopped` to `docker run`.

Example full command for production-like run:

```
docker build -t finance-triage:latest .
docker run -d --restart unless-stopped --name finance-triage -p 80:8080 finance-triage:latest
```

Security reminder:

- Use AWS security groups and firewall rules to restrict access as appropriate. Consider using an Elastic IP or load balancer for stable addressing.

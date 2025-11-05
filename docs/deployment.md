# Deploy / Run

Below, we will show a setup for deployment with caddy.

Appendix: Backend/Frontend

- Backend (Spring Boot)
    - Config: `graph.gremlin-host=<GRAPH_VM>`, `graph.gremlin-port=8182`, `metadata.aerospikeAddress=?<ASDB_VM>`,
    - pools set to 64–128.
- Frontend (Next.js)
    - Deploy Next 15 server on port 3001, behind Caddy/nginx.
    - Proxy `/api/*` and `/swagger-ui/*` to backend, everything else to Next.

Troubleshooting

- If TPS plateaus early: raise connection/workers on client and AGS.
- If latency drifts after 60–90s: inspect AGS GC logs, adjust heap and G1 settings;
  ensure server worker pools and request limits are sufficient.

---

## Set up systemd services

Once you have all of your backend configs set, and have started it to make sure it compiles and runs with
`mvn spring-boot:run`

We can start setting up both the front and backend as systemd services.

### Frontend Systemd Service

Create/edit the service for the frontend:

```bash
nano /etc/systemd/system/demo-frontend.service
```

Inside of it, paste this service file, replacing <YOUR_WEBSITE_URL> with your actual website URL:

```service
[Unit]
Description=Run the graph demo frontend
After=network.target

[Service]
Environment=BACKEND_URL=http://localhost:8080
Environment=BASE_URL=https://<YOUR_WEBSITE_URL>/api
User=demoservice
Group=website
WorkingDirectory=/var/www/graph-fraud-demo/frontend
ExecStart=/usr/bin/npm run deploy

[Install]
WantedBy=multi-user.target
```

### Backend Systemd Service

First, make sure you have packaged the backend and copied the path to the jar.

```bash
mvn clean install package
```

Create/edit the service for the backend:

```bash
nano /etc/systemd/system/demo-backend.service
```

Inside of it, paste this service file, replacing `<YOUR_WEBSITE_URL>` with your actual website URL, and `<JAR_NAME>` 
  with the name of the backend jar that was created:

```service
[Unit]
Description=Run the graph demo backend
After=network.target

[Service]
User=demoservice
Group=website
LimitNOFILE=65535
WorkingDirectory=/var/www/graph-fraud-demo/java-backend
ExecStart=/usr/bin/java -jar /var/www/graph-fraud-demo/java-backend/target/<JAR_NAME>
Restart=on-failure
SuccessExitStatus=143

[Install]
WantedBy=multi-user.target
```

## Set up Caddy

Install caddy:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
chmod o+r /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

In the systemd service for caddy, make sure the file looks like this:

```bash
sudo nano /lib/systemd/system/caddy.service
```

```shell
[Unit]
Description=Caddy
Documentation=https://caddyserver.com/docs/
After=network.target network-online.target
Requires=network-online.target

[Service]
Type=notify
User=caddy
Group=caddy
ExecStart=/usr/bin/caddy run --environ --config /etc/caddy/Caddyfile
ExecReload=/usr/bin/caddy reload --config /etc/caddy/Caddyfile --force
TimeoutStopSec=5s
LimitNOFILE=1048576
LimitNPROC=512
PrivateTmp=true
ProtectSystem=full
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
```

This should be the default caddy file, with `CAP_NET_ADMIN` added in `AmbientCapabilities`
Now edit the caddy file to configure the reverse proxy, substituting `<WEBSITE_URL>` for your actual website URL, and 
your `<MONITORING_URL>` if you are opting to use Prometheus/Grafana:

```caddyfile
<WEBSITE_URL> {
        # API → backend
        handle /api/* {
                reverse_proxy localhost:8080
        }

        # Swagger UI and OpenAPI → backend
        handle /swagger-ui/* {
                reverse_proxy localhost:8080
        }
        handle /v3/api-docs* {
                reverse_proxy localhost:8080
        }

        # Everything else → Next.js (port 3001)
        reverse_proxy localhost:3001
}

<MONITORING_URL> {
        reverse_proxy localhost:3000
}
```

## Final Steps

Now you can redirect your DNS entry to the IP of your Client VM.
Then enable and start your services!

```bash
 sudo systemctl daemon-reload
 sudo systemctl enable demo-backend
 sudo systemctl enable demo-frontend
 sudo systemctl enable caddy
```

Now you should be good to go! Check on their status to make sure they are all healthy, then your website
is online!

```bash
 sudo systemctl status demo-backend
 sudo systemctl status demo-frontend
 sudo systemctl status caddy
```

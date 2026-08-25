# weather.local reverse proxy

nginx is the only web service published to the host. It listens on port 80 for `weather.local` and proxies requests to Grafana on the private Docker Compose network at `grafana:3000`.

Grafana itself does not publish port 3000 to the host.

## Raspberry Pi hostname

Set the Raspberry Pi hostname to `weather`:

```bash
sudo hostnamectl set-hostname weather
sudo reboot
```

On Raspberry Pi OS, Avahi/mDNS normally advertises the hostname on the local network, making the Pi reachable as:

```text
http://weather.local/
```

Verify the hostname after reboot with:

```bash
hostname
```

It should print `weather`.

If `weather.local` does not resolve from a client, verify that the Pi's mDNS service is running:

```bash
systemctl status avahi-daemon
```

The reverse proxy configuration is in `nginx/default.conf`. Grafana's `GF_SERVER_DOMAIN` and `GF_SERVER_ROOT_URL` settings in `docker-compose.yml` are also configured for `weather.local`.

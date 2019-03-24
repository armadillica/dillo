# How to deploy on DO

* Create droplet with Docker preinstalled
* Add droplet IP to `/etc/hosts` a `community<nr>`
* Update `~/.ssh/config` and add `community<nr>`
* Login with `ssh community<nr>`
* Create `mkdir -p /data`
* `mount -o discard,defaults,noatime /dev/disk/by-id/scsi-0DO_Volume_volume-nyc3-01 /data`
* `echo '/dev/disk/by-id/scsi-0DO_Volume_volume-nyc3-01 /data ext4 defaults,nofail,discard 0 0' | sudo tee -a /etc/fstab`
* Install [certbot](https://certbot.eff.org/lets-encrypt/ubuntubionic-other)
* Optional: copy certs from previous droplet (rsync -avP /etc/letsencrypt/ root@community3:/etc/letsencrypt)
* Update or create `/etc/cron.d/certbot` (rsync -avP /etc/cron.d/certbot root@community3:/etc/cron.d/certbot)
* Optional: copy data from another volume with `rsync -avP /data/storage/ root@community3:/data/storage`

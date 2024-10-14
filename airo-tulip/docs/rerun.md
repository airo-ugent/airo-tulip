# Rerun

Rerun is started automatically and serves over WebSockets on port `9877` by default.
To view the logged data, set up an SSH tunnel on your local device,

```bash
ssh -N -L localhost:9877:localhost:9877 kelo@10.10.129.20
```

with `10.10.129.20` being the KELO's IP.

Then, locally,

```bash
python -m rerun ws://localhost:9877
```

You'll need to restart rerun when you restart the server on the KELO, we don't have a solution for that at this moment.

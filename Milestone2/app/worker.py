"""Background worker process: the simulator, the agent cycles, escalation and the feed threads run here so the web server (and the GPU models) never share a GIL with them."""
import os, sys, time, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, live_engine as LE
dom = importlib.import_module("domain_franchise" if config.KIND == "Franchise" else "domain_freight")
if __name__ == "__main__":
    rt = LE.Runtime(dom, int(os.environ.get("LIVE_TICK_SEC", 5)), int(os.environ.get("LIVE_CYCLE_SEC", 60)))
    if config.KIND == "Freight":
        import weather as WX; WX.start()
    while True: time.sleep(3600)

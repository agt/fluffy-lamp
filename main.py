#!/usr/bin/env python3
import logging
import sys
import time

from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

# Pod must have this key in nodeSelector to be considered
NODE_SELECTOR_KEY = "gputype"

# If this toleration key is already present, skip the pod
SKIP_TOLERATION_KEY = "gpu-class"

# Toleration to inject
INJECT_TOLERATION = {
    "key": "gpu-type",
    "operator": "Equal",
    "value": "medium",
    "effect": "NoSchedule",
}


def is_unschedulable(pod) -> bool:
    for cond in pod.status.conditions or []:
        if (
            cond.type == "PodScheduled"
            and cond.status == "False"
            and cond.reason == "Unschedulable"
        ):
            return True
    return False


def needs_patch(pod) -> bool:
    node_selector = pod.spec.node_selector or {}
    if NODE_SELECTOR_KEY not in node_selector:
        return False

    for t in pod.spec.tolerations or []:
        if t.key == SKIP_TOLERATION_KEY:
            return False
        # Already injected by a previous pass
        if t.key == INJECT_TOLERATION["key"]:
            return False

    return True


def patch_pod(v1: client.CoreV1Api, namespace: str, name: str) -> None:
    # Strategic merge patch merges tolerations by key, so existing entries are preserved.
    body = {"spec": {"tolerations": [INJECT_TOLERATION]}}
    v1.patch_namespaced_pod(name=name, namespace=namespace, body=body)
    log.info("Patched %s/%s → added toleration %s", namespace, name, INJECT_TOLERATION)


def run() -> None:
    try:
        config.load_incluster_config()
        log.info("Using in-cluster kubeconfig")
    except config.ConfigException:
        config.load_kube_config()
        log.info("Using local kubeconfig")

    v1 = client.CoreV1Api()
    w = watch.Watch()

    log.info(
        "Watching pods in all namespaces (nodeSelector key=%s, skip toleration key=%s)",
        NODE_SELECTOR_KEY,
        SKIP_TOLERATION_KEY,
    )

    while True:
        try:
            for event in w.stream(v1.list_pod_for_all_namespaces, timeout_seconds=0):
                if event["type"] not in ("ADDED", "MODIFIED"):
                    continue

                pod = event["object"]

                if pod.status.phase != "Pending":
                    continue
                if not is_unschedulable(pod):
                    continue
                if not needs_patch(pod):
                    continue

                ns = pod.metadata.namespace
                name = pod.metadata.name
                log.info("Candidate pod %s/%s — patching", ns, name)

                try:
                    patch_pod(v1, ns, name)
                except ApiException as exc:
                    log.error("Patch failed for %s/%s: %s", ns, name, exc)

        except ApiException as exc:
            log.error("Watch stream error: %s — restarting in 5 s", exc)
            time.sleep(5)
        except Exception as exc:  # noqa: BLE001
            log.error("Unexpected error: %s — restarting in 5 s", exc)
            time.sleep(5)


if __name__ == "__main__":
    run()

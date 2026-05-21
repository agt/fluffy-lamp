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

# If this toleration key is already present, skip the pod
SKIP_TOLERATION_KEY = "gpu-class"

# Maps nodeSelector gputype value → gpu-class toleration value to inject
NODE_SELECTOR_KEY = "gputype"
GPUTYPE_CLASS: dict[str, str] = {
    "a30":      "medium",
    "a5000":    "medium",
    "rtxtitan": "medium",
    "b24gb":    "medium",
    "h20gb":    "medium",
    "l40s":     "large",
    "h40gb":    "large",
    "b48gb":    "large",
}


def make_toleration(gpu_class: str) -> dict:
    return {
        "key": SKIP_TOLERATION_KEY,
        "operator": "Equal",
        "value": gpu_class,
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


def gpu_class_for(pod) -> str | None:
    """Return the gpu-class value to inject, or None if this pod is not in scope."""
    node_selector = pod.spec.node_selector or {}
    return GPUTYPE_CLASS.get(node_selector.get(NODE_SELECTOR_KEY, ""))


def needs_patch(pod) -> bool:
    if gpu_class_for(pod) is None:
        return False
    for t in pod.spec.tolerations or []:
        if t.key == SKIP_TOLERATION_KEY:
            return False
    return True


def patch_pod(v1: client.CoreV1Api, namespace: str, name: str, gpu_class: str) -> None:
    toleration = make_toleration(gpu_class)
    # Strategic merge patch merges tolerations by key, so existing entries are preserved.
    body = {"spec": {"tolerations": [toleration]}}
    v1.patch_namespaced_pod(name=name, namespace=namespace, body=body)
    log.info("Patched %s/%s → added toleration %s", namespace, name, toleration)


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
        "Watching pods in all namespaces (nodeSelector %s∈%s, skip toleration key=%s)",
        NODE_SELECTOR_KEY,
        set(GPUTYPE_CLASS),
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
                    patch_pod(v1, ns, name, gpu_class_for(pod))
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

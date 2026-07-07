# Kubernetes Overview

**Kubernetes** (often abbreviated as **K8s**) is an open-source platform for automating the deployment, scaling, and management of containerized applications. It was originally designed by Google and is now maintained by the Cloud Native Computing Foundation (CNCF).

Kubernetes groups the containers that make up an application into logical units for easy management and discovery.

## Cluster Architecture

A Kubernetes cluster consists of a **control plane** and a set of **worker nodes**.

1. The **control plane** manages the overall state of the cluster.
   - **kube-apiserver**: the front end of the control plane; all communication goes through its REST API.
   - **etcd**: a consistent and highly available key-value store used as the backing store for all cluster data.
   - **kube-scheduler**: watches for newly created Pods with no assigned node and selects a node for them to run on.
   - **kube-controller-manager**: runs controller processes, such as the node controller and the replication controller.
2. Each **worker node** runs the workloads.
   - **kubelet**: an agent that runs on each node and ensures that containers are running in a Pod.
   - **kube-proxy**: a network proxy that maintains network rules and enables Service communication.
   - **container runtime**: the software responsible for running containers, such as containerd or CRI-O.

## Core Workload Objects

**Pod** is the smallest deployable unit in Kubernetes.
- A Pod represents one or more containers that share storage, network, and a specification for how to run them.
- Containers within the same Pod share the same network namespace and can communicate via localhost.
- Pods are ephemeral: they are not restarted when they fail; instead a controller creates a replacement.

**ReplicaSet** ensures that a specified number of Pod replicas are running at any given time.

**Deployment** provides declarative updates for Pods and ReplicaSets.
- It manages rolling updates and rollbacks.
- A Deployment creates and manages a ReplicaSet, which in turn manages the Pods.
- Rolling updates replace Pods gradually to avoid downtime.

**StatefulSet** manages stateful applications.
- It provides stable, unique network identifiers and stable persistent storage for each Pod.
- Pods are created and deleted in a predictable order.

**DaemonSet** ensures that a copy of a Pod runs on all (or some) nodes, commonly used for log collectors and monitoring agents.

**Job** runs Pods that execute a task to completion, and **CronJob** runs Jobs on a repeating schedule.

## Networking and Services

**Service** is an abstraction that defines a logical set of Pods and a policy by which to access them.
- Because Pods are ephemeral and their IPs change, a Service provides a stable virtual IP (ClusterIP).
- A Service selects Pods using label selectors.
- Service types:
  - **ClusterIP**: exposes the Service on an internal cluster IP; reachable only from within the cluster. This is the default.
  - **NodePort**: exposes the Service on each node's IP at a static port.
  - **LoadBalancer**: exposes the Service externally using a cloud provider's load balancer.
  - **ExternalName**: maps the Service to a DNS name.

**Ingress** manages external HTTP and HTTPS access to Services, providing routing rules, TLS termination, and name-based virtual hosting.

**DNS** inside the cluster is provided by CoreDNS, which lets Pods resolve Services by name.

## Configuration and Storage

**ConfigMap** stores non-confidential configuration data as key-value pairs, which Pods can consume as environment variables or mounted files.

**Secret** stores sensitive data such as passwords, tokens, and keys. It is similar to a ConfigMap but intended for confidential information and is base64-encoded at rest.

**Volume** provides storage to containers in a Pod. Unlike the container's own filesystem, a Volume can outlive container restarts.
- **PersistentVolume (PV)** is a piece of storage in the cluster provisioned by an administrator or dynamically.
- **PersistentVolumeClaim (PVC)** is a request for storage by a user, which binds to a matching PV.
- **StorageClass** describes classes of storage and enables dynamic provisioning of PVs.

## Scheduling and Health

The **scheduler** assigns Pods to nodes based on resource requests, constraints, and policies.
- **Requests** are the minimum resources a container needs; the scheduler uses them to place Pods.
- **Limits** are the maximum resources a container may use; exceeding a memory limit causes the container to be terminated (OOMKilled).
- **Taints and tolerations** allow a node to repel Pods that do not tolerate the taint.
- **Node affinity** and **Pod affinity/anti-affinity** influence which nodes Pods are scheduled on.

**Probes** let the kubelet check container health.
- **Liveness probe**: determines whether a container is running; if it fails, the container is restarted.
- **Readiness probe**: determines whether a container is ready to receive traffic; if it fails, the Pod is removed from Service endpoints.
- **Startup probe**: determines whether an application within a container has started, useful for slow-starting containers.

## Namespaces and Labels

**Namespace** provides a mechanism for isolating groups of resources within a single cluster, commonly used to separate environments or teams.

**Labels** are key-value pairs attached to objects, used to organize and select subsets of objects. **Selectors** use labels to identify a group of objects, for example when a Service targets its Pods.

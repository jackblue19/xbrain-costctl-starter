import boto3

from commands._common import tags_match


def list_ecs(want, missing):
    """
    List ECS services (works for Fargate too)

    Returns:
    [
        (
            service_name,
            launch_type,
            status,
            tags
        )
    ]
    """

    ecs = boto3.client("ecs")

    rows = []

    clusters = ecs.list_clusters()["clusterArns"]

    for cluster_arn in clusters:

        services = ecs.list_services(cluster=cluster_arn)["serviceArns"]

        if not services:
            continue

        desc = ecs.describe_services(
            cluster=cluster_arn, services=services, include=["TAGS"]
        )

        for svc in desc["services"]:

            tags = {t["key"]: t["value"] for t in svc.get("tags", [])}

            if not tags_match(tags, want, missing):
                continue

            rows.append(
                (
                    svc["serviceName"],
                    svc.get("launchType", "unknown"),
                    svc["status"],
                    tags,
                )
            )

    return rows

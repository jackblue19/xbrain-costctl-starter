"""list — list AWS resources by type, filter by tag / missing-tag.

WHAT YOU MUST BUILD
-------------------
Support 4 resource types: ec2, rds, s3, volume.
Each takes:
- `want` — list of (key, value) tag pairs the resource MUST have
- `missing` — list of tag keys the resource MUST NOT have

Print a formatted table to stdout. Test cases are in tests/test_list.py.

HELPERS YOU CAN USE
-------------------
From commands._common:
  parse_kv(s) -> (k, v)            # "Owner=alice" -> ("Owner", "alice")
  tags_to_dict(items) -> dict       # boto3 [{"Key","Value"}] -> {k: v}
  tags_match(tags, want, missing) -> bool

AWS APIS YOU'LL NEED
--------------------
- EC2: ec2.describe_instances() with get_paginator
- RDS: rds.describe_db_instances(), then list_tags_for_resource(ResourceName=arn)
- S3:  s3.list_buckets(), then get_bucket_tagging(Bucket=name)
       (catch ClientError when bucket has no tagging config — treat as {})
- EBS: ec2.describe_volumes() with get_paginator

EXPECTED OUTPUT FORMAT (when run from CLI)
------------------------------------------
    EC2 Environment=dev — 1 found:
    ------------------------------------------------------------------------------
      i-0abc123def456789a       t3.micro       running       Environment=dev

VERIFY
------
    pytest tests/test_list.py -v
"""

import boto3
from botocore.exceptions import ClientError

from commands._common import parse_kv, tags_to_dict, tags_match


def _list_ec2(want, missing):
    """
    List EC2 instances matching tag filters.

    Returns:
        list of (instance_id, instance_type, state, tags_dict)
    """
    ec2 = boto3.client("ec2")
    rows = []

    paginator = ec2.get_paginator("describe_instances")

    for page in paginator.paginate():
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                tags = tags_to_dict(instance.get("Tags", []))

                if not tags_match(tags, want, missing):
                    continue

                rows.append(
                    (
                        instance.get("InstanceId", ""),
                        instance.get("InstanceType", ""),
                        instance.get("State", {}).get("Name", ""),
                        tags,
                    )
                )

    return rows


def _list_rds(want, missing):
    """
    List RDS DB instances matching tag filters.

    Returns:
        list of (db_id, db_class, db_status, tags_dict)
    """
    rds = boto3.client("rds")
    rows = []

    resp = rds.describe_db_instances()

    for db in resp.get("DBInstances", []):
        arn = db["DBInstanceArn"]

        tag_resp = rds.list_tags_for_resource(ResourceName=arn)
        tags = tags_to_dict(tag_resp.get("TagList", []))

        if not tags_match(tags, want, missing):
            continue

        rows.append(
            (
                db.get("DBInstanceIdentifier", ""),
                db.get("DBInstanceClass", ""),
                db.get("DBInstanceStatus", ""),
                tags,
            )
        )

    return rows


def _list_s3(want, missing):
    """
    List S3 buckets matching tag filters.

    Returns:
        list of (bucket_name, "bucket", "active", tags_dict)
    """
    s3 = boto3.client("s3")
    rows = []

    resp = s3.list_buckets()

    for bucket in resp.get("Buckets", []):
        name = bucket["Name"]

        try:
            tag_resp = s3.get_bucket_tagging(Bucket=name)
            tags = tags_to_dict(tag_resp.get("TagSet", []))
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            # S3 raises this when bucket has no tags.
            if code in ("NoSuchTagSet", "NoSuchTagSetError"):
                tags = {}
            else:
                raise

        if not tags_match(tags, want, missing):
            continue

        rows.append((name, "bucket", "active", tags))

    return rows


def _list_volume(want, missing):
    """
    List EBS volumes matching tag filters.

    Returns:
        list of (volume_id, "type-sizeGB", state, tags_dict)
    """
    ec2 = boto3.client("ec2")
    rows = []

    paginator = ec2.get_paginator("describe_volumes")

    for page in paginator.paginate():
        for volume in page.get("Volumes", []):
            tags = tags_to_dict(volume.get("Tags", []))

            if not tags_match(tags, want, missing):
                continue

            volume_type = volume.get("VolumeType", "")
            size = volume.get("Size", "")
            type_size = f"{volume_type}-{size}GB"

            rows.append(
                (
                    volume.get("VolumeId", ""),
                    type_size,
                    volume.get("State", ""),
                    tags,
                )
            )

    return rows


DISPATCH = {
    "ec2": _list_ec2,
    "rds": _list_rds,
    "s3": _list_s3,
    "volume": _list_volume,
}


def _format_tags(tags):
    if not tags:
        return "-"

    return ", ".join(f"{k}={v}" for k, v in sorted(tags.items()))


def run(args):
    """
    Entry point called by costctl.py.
    """
    want = [parse_kv(t) for t in args.tag]
    missing = args.missing_tag

    rows = DISPATCH[args.type](want, missing)

    filters = []
    filters.extend(f"{k}={v}" for k, v in want)
    filters.extend(f"missing:{k}" for k in missing)

    filter_text = ", ".join(filters) if filters else "all"
    title = f"{args.type.upper()} {filter_text} — {len(rows)} found:"

    print(title)
    print("-" * 78)

    for rid, kind, state, tags in rows:
        print(f"{rid:<32} {kind:<16} {state:<16} {_format_tags(tags)}")

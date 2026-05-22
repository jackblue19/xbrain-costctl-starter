"""cost — show cost of resources matching a tag, over the last N days.

WHAT YOU MUST BUILD
-------------------
A function that:
  1. Queries Cost Explorer (`ce.get_cost_and_usage`) for the last N days
  2. Filters by a tag (e.g. Application=HealthBot)
  3. Groups by SERVICE dimension
  4. Sums per-service costs across the date range
  5. Prints services sorted descending by cost, plus a TOTAL row

HELPERS YOU CAN USE
-------------------
From commands._common:
  parse_kv(s) -> (k, v)             # "Application=HealthBot" -> tuple

AWS APIS YOU'LL NEED
--------------------
ce = boto3.client("ce")
ce.get_cost_and_usage(
    TimePeriod={"Start": "YYYY-MM-DD", "End": "YYYY-MM-DD"},
    Granularity="DAILY",
    Metrics=["UnblendedCost"],
    Filter={"Tags": {"Key": "<tag_key>", "Values": ["<tag_value>"]}},
    GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
)

The response has `ResultsByTime` (one entry per day), each with `Groups` —
each group has `Keys=[service_name]` and `Metrics={"UnblendedCost":{"Amount":"1.23"}}`.

EXPECTED OUTPUT FORMAT
----------------------
    Cost for Application=HealthBot over last 7 days (2026-05-14 → 2026-05-21):
    ------------------------------------------------------------
      Amazon Elastic Compute Cloud - Compute        $    8.42
      Amazon Relational Database Service             $    5.18
      ...
    ------------------------------------------------------------
      TOTAL                                          $   13.80

GOTCHAS
-------
- Cost data lags 8–24h. If --days 1 returns nothing, try --days 7.
- Tag filter requires that you have ACTIVATED cost allocation tags in Billing.
- Amount field is a STRING in the response — cast to float before summing.

VERIFY MANUALLY (no test file for this command)
-----------------------------------------------
    ./costctl.py cost --tag Application=<your-app> --days 7

The first time you run this, double-check against the AWS Console
(Cost Management → Cost Explorer → filter by same tag + same range).
Output should match within a few cents.
"""

"""cost — show cost of resources matching a tag, over the last N days."""

import boto3
from collections import defaultdict
from datetime import date, timedelta
from botocore.exceptions import ClientError

from commands._common import parse_kv


def run(args):
    """
    Entry point.
    """
    tag_key, tag_val = parse_kv(args.tag)

    end = date.today()
    start = end - timedelta(days=args.days)

    ce = boto3.client("ce")

    try:
        resp = ce.get_cost_and_usage(
            TimePeriod={
                "Start": start.isoformat(),
                "End": end.isoformat(),
            },
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            Filter={
                "Tags": {
                    "Key": tag_key,
                    "Values": [tag_val],
                }
            },
            GroupBy=[
                {
                    "Type": "DIMENSION",
                    "Key": "SERVICE",
                }
            ],
        )
    except ClientError as e:
        err = e.response.get("Error", {})
        code = err.get("Code", "Unknown")
        message = err.get("Message", str(e))
        print(f"AWS error [{code}]: {message}")
        return

    totals = defaultdict(float)

    for day in resp.get("ResultsByTime", []):
        for group in day.get("Groups", []):
            service = group.get("Keys", ["Unknown"])[0]
            amount = (
                group.get("Metrics", {}).get("UnblendedCost", {}).get("Amount", "0")
            )
            totals[service] += float(amount)

    print(
        f"Cost for {tag_key}={tag_val} over last {args.days} days "
        f"({start.isoformat()} → {end.isoformat()}):"
    )
    print("-" * 60)

    if not totals:
        print(
            "No cost data found. Try a larger --days value or activate cost allocation tags."
        )
        print("-" * 60)
        print("TOTAL                                            $ 0.00")
        return

    grand_total = 0.0

    for service, amount in sorted(
        totals.items(), key=lambda item: item[1], reverse=True
    ):
        grand_total += amount
        print(f"{service:<48} $ {amount:,.2f}")

    print("-" * 60)
    print(f"{'TOTAL':<48} $ {grand_total:,.2f}")

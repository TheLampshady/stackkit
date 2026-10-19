"""Detect the traffic split of an App Engine service that splits "by cookie".

Reports the split two ways:

1. COOKIE (forced) -- sweeps ``GOOGAPPUID`` 0-999. Deterministic shard map: exactly
   which cookie values route to which version, and each version's % of the 1000
   shards. This is where you get a reusable cookie value to view a page.
2. NO-COOKIE (sampled) -- fires N requests with no ``GOOGAPPUID``. App Engine assigns
   a masked random value per request, so this estimates the LIVE split a fresh
   visitor actually gets. (The masked value is not easily reusable, which is why
   the cookie to set comes from the sweep.)

It then prints a side-by-side comparison and a diff of the minority vs majority page
so you can see how they differ without knowing it in advance.

Background: ``GOOGAPPUID`` is an integer 0-999. App Engine builds 1000 shards and
gives each version a share proportional to its traffic %. A 1% version owns ~10
values.

Grouping signature (used for both runs) is, in priority order:

- ``--version-header NAME`` -> group by that response header (ground truth; have your
  app echo ``os.environ["GAE_VERSION"]``)
- ``--marker "text"`` -> group by presence of a stable substring
- (default) -> SHA-256 of the response body

Header or marker grouping makes the two runs line up cleanly even if the page has
per-request noise (CSRF tokens, timestamps, asset hashes).
"""

import asyncio
import difflib
import hashlib
import os
from collections import defaultdict
from typing import Annotated

import aiohttp
import typer

#: Cap per-representative body (chars) to bound memory during a full sweep.
MAX_STORED_BODY = 500_000

#: Number of ``GOOGAPPUID`` shards App Engine allocates across versions.
SHARD_COUNT = 1000

Signature = str
SweepBuckets = dict[Signature, list[int]]
SampleCounts = dict[Signature, int]
Representatives = dict[Signature, str]


def resolve_url(url: str | None) -> str:
    """Resolve the target URL from the argument or the environment.

    Falls back to ``GAE_URL``, then to ``https://{PROJECT_ID}.appspot.com/``.

    :param url: URL passed on the command line, if any
    :return: A fully qualified URL to probe
    :raises typer.BadParameter: If no URL can be resolved
    """
    if url:
        return url

    env_url = os.getenv("GAE_URL")
    if env_url:
        return env_url

    project_id = os.getenv("PROJECT_ID")
    if project_id:
        return f"https://{project_id}.appspot.com/"

    raise typer.BadParameter(
        "No URL given and neither GAE_URL nor PROJECT_ID is set in .env",
        param_hint="URL",
    )


async def probe(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    url: str,
    key: int,
    uid: int | None,
    cachebust: bool,
    marker: str | None,
    version_header: str | None,
) -> tuple[int, Signature, str]:
    """Issue one request and reduce the response to a grouping signature.

    :param session: Shared client session (cookies disabled)
    :param sem: Concurrency limiter
    :param url: Target URL
    :param key: Identifier for this request (the cookie value during a sweep)
    :param uid: ``GOOGAPPUID`` to force, or None to send no cookie at all
    :param cachebust: Append a unique query param to dodge proxy caches
    :param marker: Group by presence of this substring
    :param version_header: Group by this response header's value
    :return: The key, the signature, and the response body
    """
    target = url
    if cachebust:
        sep = "&" if "?" in url else "?"
        target = f"{url}{sep}_cb={key}"

    headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
    if uid is not None:
        headers["Cookie"] = f"GOOGAPPUID={uid}"

    async with sem:
        try:
            async with session.get(target, headers=headers) as resp:
                raw = await resp.read()
                body = raw.decode("utf-8", "ignore")
                if resp.status != 200:
                    return key, f"HTTP_{resp.status}", body
                if version_header:
                    return key, resp.headers.get(version_header, "MISSING"), body
                if marker:
                    return key, f"marker_present={marker in body}", body
                return key, hashlib.sha256(raw).hexdigest()[:12], body
        except Exception as exc:  # noqa: BLE001 - one bad probe must not kill the run
            return key, f"ERROR:{type(exc).__name__}", ""


async def run(
    url: str,
    concurrency: int,
    sample_size: int,
    cachebust: bool,
    marker: str | None,
    version_header: str | None,
) -> tuple[SweepBuckets, SampleCounts, Representatives]:
    """Run the forced-cookie sweep and the no-cookie sample.

    :param url: Target URL
    :param concurrency: Max in-flight requests
    :param sample_size: No-cookie requests to sample (0 skips the sample)
    :param cachebust: Append a unique query param to dodge proxy caches
    :param marker: Group by presence of this substring
    :param version_header: Group by this response header's value
    :return: Sweep buckets (signature -> cookie values), sample counts
        (signature -> hits), and one representative body per signature
    """
    sem = asyncio.Semaphore(concurrency)
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(
        timeout=timeout, cookie_jar=aiohttp.DummyCookieJar()
    ) as session:
        # Forced-cookie sweep: keys ARE the cookie values.
        sweep_res = await asyncio.gather(
            *[
                probe(session, sem, url, uid, uid, cachebust, marker, version_header)
                for uid in range(SHARD_COUNT)
            ]
        )
        # No-cookie sample: uid=None so no GOOGAPPUID is sent.
        sample_res: list[tuple[int, Signature, str]] = []
        if sample_size > 0:
            sample_res = list(
                await asyncio.gather(
                    *[
                        probe(
                            session,
                            sem,
                            url,
                            i,
                            None,
                            cachebust,
                            marker,
                            version_header,
                        )
                        for i in range(sample_size)
                    ]
                )
            )

    sweep_buckets: SweepBuckets = defaultdict(list)
    sample_counts: SampleCounts = defaultdict(int)
    reps: Representatives = {}
    for key, sig, body in sweep_res:
        sweep_buckets[sig].append(key)
        reps.setdefault(sig, body[:MAX_STORED_BODY])
    for _key, sig, body in sample_res:
        sample_counts[sig] += 1
        reps.setdefault(sig, body[:MAX_STORED_BODY])

    return dict(sweep_buckets), dict(sample_counts), reps


def report(
    sweep_buckets: SweepBuckets,
    sample_counts: SampleCounts,
    reps: Representatives,
    sample_size: int,
    diff_lines: int,
) -> None:
    """Print the shard map, the live split, and the minority/majority diff.

    :param sweep_buckets: Signature -> cookie values that routed to it
    :param sample_counts: Signature -> no-cookie hit count
    :param reps: Signature -> representative response body
    :param sample_size: Requested no-cookie sample size
    :param diff_lines: Max diff lines to print
    :side effects: Writes to stdout
    """
    sweep_total = sum(len(v) for v in sweep_buckets.values())
    sample_total = sum(sample_counts.values())
    ordered = sorted(sweep_buckets.items(), key=lambda kv: len(kv[1]))  # smallest first

    typer.secho(
        f"\n=== COOKIE (forced): swept {sweep_total} GOOGAPPUID values -> "
        f"{len(sweep_buckets)} group(s) ===\n",
        bold=True,
    )
    for sig, uids in ordered:
        pct = 100.0 * len(uids) / sweep_total if sweep_total else 0.0
        sample = ", ".join(str(u) for u in uids[:8])
        more = " ..." if len(uids) > 8 else ""
        typer.echo(f"  [{pct:5.1f}%]  {len(uids):4d} values  sig={sig}")
        typer.echo(f"            example GOOGAPPUID values: {sample}{more}")
    typer.echo("")

    if sample_size > 0:
        typer.secho(
            f"=== NO-COOKIE (sampled): {sample_total} random requests -> "
            f"{len(sample_counts)} group(s) ===\n",
            bold=True,
        )
        for sig, cnt in sorted(sample_counts.items(), key=lambda kv: kv[1]):
            pct = 100.0 * cnt / sample_total if sample_total else 0.0
            typer.echo(f"  [{pct:5.1f}%]  {cnt:4d} hits    sig={sig}")
        typer.echo("")

        # Side-by-side over the union of signatures.
        typer.secho(
            "=== COMPARISON (cookie shard-map vs live no-cookie split) ===\n", bold=True
        )
        typer.echo(f"  {'signature':<16}  {'cookie %':>9}  {'no-cookie %':>12}")
        typer.echo(f"  {'-' * 16}  {'-' * 9}  {'-' * 12}")
        for sig in sorted(
            set(sweep_buckets) | set(sample_counts),
            key=lambda s: -len(sweep_buckets.get(s, [])),
        ):
            c_pct = (
                100.0 * len(sweep_buckets.get(sig, [])) / sweep_total
                if sweep_total
                else 0.0
            )
            s_cnt = sample_counts.get(sig, 0)
            s_pct = (
                f"{100.0 * s_cnt / sample_total:>11.1f}%"
                if sample_total
                else "     n/a"
            )
            c_str = f"{c_pct:>8.1f}%" if sig in sweep_buckets else "      --"
            typer.echo(f"  {sig:<16}  {c_str}  {s_pct}")
        typer.echo("")
        if sample_total and sample_total < 3000:
            typer.echo(
                "  Note: small samples are noisy. A true 1% version yields only ~1%"
            )
            typer.echo(
                "  of hits, so bump --sample-size (e.g. 5000+) for a tighter estimate.\n"
            )

    if len(ordered) == 1:
        typer.echo("-" * 62)
        typer.secho(
            "Only ONE group in the sweep -- every value returned the same bytes.",
            fg=typer.colors.YELLOW,
        )
        typer.echo(
            "The versions likely render identically at this URL, or the page has"
        )
        typer.echo("per-request noise. Try another path, --marker on stable text, or")
        typer.echo("--version-header for ground truth.")
        return

    smallest_sig, smallest_uids = ordered[0]
    largest_sig, largest_uids = ordered[-1]

    typer.echo("-" * 62)
    typer.secho(
        "Most likely your small-sample (e.g. 1%) version:",
        fg=typer.colors.GREEN,
        bold=True,
    )
    typer.echo(f"  signature : {smallest_sig}")
    typer.echo(f"  set cookie: GOOGAPPUID={smallest_uids[0]}")
    typer.echo(
        "\nView it in a browser: open DevTools console on your app's domain and run"
    )
    typer.echo(f'  document.cookie = "GOOGAPPUID={smallest_uids[0]}; path=/";')
    typer.echo("then reload. Or from the shell:")
    typer.echo(f'  curl -s -H "Cookie: GOOGAPPUID={smallest_uids[0]}" <url> | head')

    a = reps.get(smallest_sig, "").splitlines()
    b = reps.get(largest_sig, "").splitlines()
    diff = list(
        difflib.unified_diff(
            b,
            a,
            fromfile=f"MAJORITY ({len(largest_uids)} values)",
            tofile=f"MINORITY ({len(smallest_uids)} values)",
            lineterm="",
        )
    )
    typer.echo("\n" + "-" * 62)
    if diff:
        typer.secho(
            f"How the minority page differs from the majority page "
            f"(first {diff_lines} lines):\n",
            bold=True,
        )
        for line in diff[:diff_lines]:
            color = None
            if line.startswith("+"):
                color = typer.colors.GREEN
            elif line.startswith("-"):
                color = typer.colors.RED
            elif line.startswith("@@"):
                color = typer.colors.CYAN
            typer.secho(line, fg=color)
        if len(diff) > diff_lines:
            typer.echo(f"... ({len(diff) - diff_lines} more diff lines)")
    else:
        typer.echo("Groups differ by signature but the stored bodies look identical")
        typer.echo("(likely header- or marker-based grouping).")


def split_cookie(
    url: Annotated[
        str | None,
        typer.Argument(
            metavar="URL",
            help="Full URL to probe. Defaults to $GAE_URL, "
            "then https://$PROJECT_ID.appspot.com/",
        ),
    ] = None,
    concurrency: Annotated[
        int, typer.Option("--concurrency", "-c", min=1, help="Max concurrent requests")
    ] = 25,
    sample_size: Annotated[
        int,
        typer.Option(
            "--sample-size",
            "-n",
            min=0,
            help="No-cookie requests to sample for the live split (0 = sweep only)",
        ),
    ] = 1000,
    cachebust: Annotated[
        bool,
        typer.Option(
            "--cachebust/--no-cachebust",
            help="Append a unique query param per request to dodge proxy caches",
        ),
    ] = False,
    marker: Annotated[
        str | None,
        typer.Option(
            "--marker",
            help="Group by presence of this substring instead of a body hash",
        ),
    ] = None,
    version_header: Annotated[
        str | None,
        typer.Option(
            "--version-header",
            help="Group by this response header's value (ground truth if the app "
            "echoes GAE_VERSION). Defaults to $GAE_VERSION_HEADER",
        ),
    ] = None,
    diff_lines: Annotated[
        int, typer.Option("--diff-lines", min=0, help="Max diff lines to print")
    ] = 60,
) -> None:
    """Report a GAE cookie-split: forced-cookie shard map vs live no-cookie split."""
    target = resolve_url(url)
    header = version_header or os.getenv("GAE_VERSION_HEADER")

    typer.secho(f"Probing {target}", fg=typer.colors.BRIGHT_BLACK)
    sweep_buckets, sample_counts, reps = asyncio.run(
        run(target, concurrency, sample_size, cachebust, marker, header)
    )
    report(sweep_buckets, sample_counts, reps, sample_size, diff_lines)

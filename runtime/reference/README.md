# Private execution routes
When several tasks share computer use, read [resource admission and continuation](../../skills/media-master/references/computer-use-queue.md) and resolve a supported private host binding. The local runner's durable occurrences are separate from global desktop waiting and native continuation. A runner queue or periodic wake alone proves no release-triggered resumption. Preserve original paused/cadence/freshness policies; retire overdue work with a recorded disposition instead of silent loss or a catch-up burst.


Use [scheduled host computer use](BROWSER_HOST.md) when the local Codex turn should execute the workflow and operate Chrome or another selected browser. This route uses the installed computer-use plugin and requires no API connector.

The command-runner route has these requirements: Python 3.9+ with SQLite and IANA timezone data. The command runner is local and provider-neutral; no network connection, account or model is activated. The command runner includes a synthetic write adapter. The host route uses browser_host.py for queue/receipt bookkeeping and the host’s real computer controls for effects. Command-based live adapters remain separate; no live scheduled send is claimed by the local tests.

Ask the assistant to complete the disabled operating-plan template from your publication choices. Keep the resulting plan and workspace outside this library. Set your actual IANA timezone, interval UTC anchor or calendar time/weekdays, explicit DST fold policy (first/second/both; nonexistent times skip), active sending windows, freshness, overlap, bounded retries, budgets, scoped authorization and executor. Do not reuse demonstration schedules as defaults.

Commands, from this directory (replace the arguments with your private paths):

```text
python3 runner.py --workspace PRIVATE_PATH configure PLAN_PATH
python3 runner.py --workspace PRIVATE_PATH run
python3 runner.py --workspace PRIVATE_PATH status
python3 runner.py --workspace PRIVATE_PATH pause system
python3 runner.py --workspace PRIVATE_PATH resume system
python3 runner.py --workspace PRIVATE_PATH stop
```

Pause scopes: system, publication:ID, account:ID, workflow:JOB_KIND and job:ID. Pauses are checked before effects as well as claims. A stop ends the polling process after the current bounded executor returns; pause first when effects must be held. Already submitted remote operations require reconciliation. Never assume a remote scheduled post was cancelled by local pause.

Intervals are anchored elapsed UTC time; calendars use the configured timezone. Catch-up coalesces to the latest slot and applies freshness/skip/review. This small reference runner deliberately does not replay every missed occurrence. Repeated local wall times follow the chosen policy but missed occurrences coalesce. Moving clocks backwards do not reset the prior high-water mark. Health reports the actual last heartbeat, unknown actions, listener gaps and pauses. No offline alert service is provisioned.

Use export_workspace only for a specifically authorized private backup, with an explicit file inventory. Credentials must never be stored in the database. Restore verifies hashes and publication identity into an empty destination. Keep unresolved/omitted references visible; a partial export is not full restoration.

Start no permanent OS service as part of installing skills. Live deployment, real provider spending and external actions require the owner's configured scope. Synthetic test processes are finite and stopped after verification.

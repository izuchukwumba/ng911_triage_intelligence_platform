# Replay streams

Timed message sequences for stream replay (design v1.2, section 10.2). All
data here is **synthetic**.

One JSON object per line, in order:

| Field | Meaning |
|---|---|
| `offset_s` | Seconds since the start of the stream; must not decrease |
| `incident` | Stream-local key grouping messages into one incident |
| `text` | The message |
| `source_type` | Optional; defaults to `synthetic_transcript` |

## `escalation.jsonl`

Four interleaved incidents over two and a half minutes. Two of them escalate
through follow-up messages: smoke becomes a fire with people trapped, and a
fall becomes "not breathing". One de-escalates. The replay shows when each
incident reached the top of the queue.

```sh
cd backend
python -m ntip.stream ../data/streams/escalation.jsonl --candidate research-1.0.0
```

# SteerPlane — TypeScript SDK

**Runtime control plane for autonomous AI agents.**

> `npm install steerplane`

## Quick Start

### Higher-Order Function (Simplest)

```typescript
import { guard } from 'steerplane';

const runAgent = guard(
  async () => {
    // Your agent code here
    await agent.run();
  },
  {
    agentName: 'support_bot',
    maxCostUsd: 10.00,
    maxSteps: 50,
  }
);

await runAgent();
```

### Class API (Full Control)

```typescript
import { SteerPlane } from 'steerplane';

const sp = new SteerPlane({ agentId: 'my_bot' });

await sp.run(async (run) => {
  await run.logStep({ action: 'query_db', tokens: 380, cost: 0.002 });
  await run.logStep({ action: 'call_llm', tokens: 1240, cost: 0.008 });
  await run.logStep({ action: 'send_email', tokens: 120, cost: 0.001 });
}, { maxCostUsd: 10 });
```

### Manual Lifecycle

```typescript
import { SteerPlane } from 'steerplane';

const sp = new SteerPlane({ agentId: 'my_bot' });
const run = sp.createRun({ maxCostUsd: 10 });

await run.start();
await run.logStep({ action: 'search', tokens: 100, cost: 0.001 });
await run.logStep({ action: 'generate', tokens: 1240, cost: 0.008 });
await run.end();
```

## Features

| Feature | Description |
|---------|-------------|
| 🔄 **Loop Detection** | Sliding-window pattern detector catches repeating agent behavior |
| 💰 **Cost Limits** | Hard USD ceiling per run — terminate instantly when exceeded |
| 🚫 **Step Limits** | Cap maximum execution steps |
| 📊 **Telemetry** | Every step logged to the SteerPlane dashboard |
| 🛡️ **Graceful Degradation** | If API is down, guards still work locally |
| ⚡ **Zero Dependencies** | Uses native `fetch` — no bloat |

## Error Handling

```typescript
import { guard, CostLimitExceeded, LoopDetectedError } from 'steerplane';

const runAgent = guard(async () => {
  try {
    await agent.run();
  } catch (err) {
    if (err instanceof CostLimitExceeded) {
      console.log(`Budget exceeded: ${err.currentCost}`);
    }
    if (err instanceof LoopDetectedError) {
      console.log(`Loop pattern: ${err.pattern}`);
    }
  }
}, { maxCostUsd: 5 });
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STEERPLANE_API_URL` | `http://localhost:8000` | SteerPlane API server URL |

## Requirements

- Node.js 18+
- SteerPlane API server running (for dashboard integration)

## License

MIT

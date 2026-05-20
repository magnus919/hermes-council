╔══════════════════════════════════════════════════════════════╗
║  Council Synthesis: WebSockets vs Server-Sent Events        ║
║  for Real-Time Notifications                                ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Panel:                                                      ║
║    Elena Vasquez — Infra engineer (Twilio/Slack/Ably)        ║
║    James Okonkwo — Mobile/web networks specialist            ║
║    Marcus Chen — Backend/systems architect                   ║
║    Priya Mehta — Proxy/CDN infrastructure engineer           ║
║                                                              ║
║  Mode: medium • Rounds: 2 (position + cross-examination)     ║
║                                                              ║
║  ── Points of Consensus ──                                   ║
║                                                              ║
║  • SSE is the correct architectural default for               ║
║    unidirectional server-to-client notification workloads.    ║
║    All four agents agree on this.                            ║
║                                                              ║
║  • WebSocket is necessary when the client needs to send      ║
║    data at equivalent frequency (collaborative editing,       ║
║    live market data with order entry, multiplayer games).    ║
║                                                              ║
║  • The protocol should match the data flow, not the hype.    ║
║    Choosing WebSocket because "it's modern" is a mistake.     ║
║                                                              ║
║  ── Points of Divergence ──                                  ║
║                                                              ║
║  1. The "complexity is free" claim                           ║
║     Elena: SSE runs on HTTP — every intermediary already     ║
║     handles it. WebSocket requires explicit proxy config,    ║
║     custom health checks, and dedicated connection mgmt.     ║
║     Marcus: SSE still needs connection registry, channel     ║
║     management, auth rotation, monitoring. The complexity    ║
║     is not free — it's just different.                       ║
║     → Verdict: Both are right. SSE's operational surface     ║
║       is smaller but not zero.                               ║
║                                                              ║
║  2. The "just works on HTTP" claim                           ║
║     Elena: SSE rides on standard HTTP infrastructure, which  ║
║     makes debugging simpler (HTTP status codes, clear errors) ║
║     Priya: Intermediaries BUFFER HTTP responses. Nginx       ║
║     proxy_buffering on, Cloudflare edge, Zscaler, Sophos —  ║
║     each layer adds latency. SSE doesn't "just work"         ║
║     through real-world proxy chains.                         ║
║     → Verdict: Elena wins for controlled infra, Priya wins   ║
║       for enterprise/heterogeneous environments.             ║
║                                                              ║
║  3. HTTP/2 backpressure (Priya's unique finding)             ║
║     If a single SSE stream falls behind on HTTP/2, the       ║
║     flow control window closes and BLOCKS all multiplexed    ║
║     streams on that connection — including colocated API     ║
║     traffic. None of the other agents flagged this.          ║
║     → This is a critical insight that deserves weight.       ║
║                                                              ║
║  4. Adverse network conditions                               ║
║     James: WebSocket still wins for mobile carriers, public  ║
║     WiFi, captive portals, 2G/3G transitions. SSE with a    ║
║     well-designed reconnection layer is close but not there. ║
║     → James moderated significantly after reading others.   ║
║       His final position converged toward SSE for 80%.       ║
║                                                              ║
║  5. Browser connection limits                                ║
║     Marcus: ~6 EventSource connections per origin in Chrome. ║
║     If you architect many distinct notification channels     ║
║     as separate SSE streams, you hit this ceiling.           ║
║     → Solution: multiplex channels within one SSE stream.    ║
║                                                              ║
║  ── Key Insights ──                                          ║
║                                                              ║
║  • The debate reached genuine convergence: SSE for 80%       ║
║    of notification use cases, WebSocket for the remaining     ║
║    20% (bidirectional, sub-100ms, mobile-first).             ║
║                                                              ║
║  • The real disagreement isn't about protocol capabilities — ║
║    it's about which failure modes you've experienced.        ║
║    Each agent's position is shaped by the fires they've      ║
║    fought, and all are valid.                                ║
║                                                              ║
║  • The most novel insight (HTTP/2 backpressure) came from    ║
║    the agent with the most unexpected background (proxy      ║
║    infrastructure engineer on a real-time debate panel).     ║
║    This validates the composition strategy of seeking        ║
║    non-obvious perspectives.                                 ║
║                                                              ║
║  ── Recommendation ──                                        ║
║                                                              ║
║  Default to SSE for server-to-client notifications.          ║
║  Use WebSocket when:                                         ║
║    - Client sends data at near-equivalent frequency          ║
║    - Sub-100ms latency is a measured requirement             ║
║    - Primary audience is mobile on adverse networks          ║
║    - Payloads are binary (SSE is text-only natively)        ║
║                                                              ║
║  Before committing to SSE:                                   ║
║    - Audit your proxy chain for buffering (weight: HIGH)     ║
║    - Design for HTTP/2 backpressure isolation (weight: HIGH) ║
║    - Account for browser connection limits (weight: MEDIUM)  ║
║    - Build reconnection with Last-Event-ID (weight: MEDIUM)  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

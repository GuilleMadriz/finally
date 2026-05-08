"""System prompt + message assembly for the FinAlly chat LLM."""

from __future__ import annotations

from .schemas import ChatTurn, PortfolioContext

SYSTEM_PROMPT = (
    "You are FinAlly, an AI trading assistant inside a simulated portfolio "
    "workstation. You help the user analyze their portfolio, suggest and execute "
    "trades, and manage their watchlist.\n\n"
    "Guidelines:\n"
    "- Analyze portfolio composition, risk concentration, and unrealized P&L when relevant.\n"
    "- Suggest trades with brief reasoning. Execute trades when the user asks or agrees.\n"
    "- Manage the watchlist proactively when the user expresses interest in tickers.\n"
    "- Be concise and data-driven. No fluff.\n"
    "- All money is simulated, so trades execute instantly without confirmation dialogs.\n"
    "- Respond ONLY with valid JSON matching the required schema. The 'message' field is the "
    "conversational reply shown to the user. Use 'trades' to execute trades and "
    "'watchlist_changes' to add or remove tickers. Leave those arrays empty when no action "
    "is needed."
)


def _format_portfolio(ctx: PortfolioContext) -> str:
    """Render the portfolio snapshot as a compact text block for the LLM."""
    lines: list[str] = [
        "Current portfolio state:",
        f"- Cash balance: ${ctx.cash_balance:,.2f}",
        f"- Total value (cash + positions): ${ctx.total_value:,.2f}",
    ]

    if ctx.positions:
        lines.append("Positions:")
        for p in ctx.positions:
            lines.append(
                f"  - {p.ticker}: qty={p.quantity:g} avg_cost=${p.avg_cost:,.2f} "
                f"price=${p.current_price:,.2f} "
                f"pnl=${p.unrealized_pnl:,.2f} ({p.pnl_percent:+.2f}%)"
            )
    else:
        lines.append("Positions: (none)")

    if ctx.watchlist:
        lines.append("Watchlist:")
        for w in ctx.watchlist:
            lines.append(f"  - {w.ticker}: ${w.price:,.2f}")
    else:
        lines.append("Watchlist: (empty)")

    return "\n".join(lines)


def build_messages(
    portfolio_ctx: PortfolioContext,
    history: list[ChatTurn],
    user_message: str,
) -> list[dict[str, str]]:
    """Build the OpenAI-style messages array for a single chat turn.

    The portfolio context is injected as a fresh system message every turn so the
    LLM always sees up-to-date prices and positions, regardless of history length.
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": _format_portfolio(portfolio_ctx)},
    ]
    for turn in history:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": user_message})
    return messages

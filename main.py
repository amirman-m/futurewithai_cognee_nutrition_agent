"""
main.py — Entry Point & Interactive Chat Loop
==============================================
Single responsibility: wire up the agent, run first-time profile setup,
and host the interactive CLI loop.

Why the profile is stored every run (for now):
  In production you would check whether the user already has a Cognee
  dataset and skip this step. For educational purposes, calling
  store_user_profile() on each run is idempotent — it overwrites the
  profile with the same data — so it is safe and keeps this file simple.
  See the README for the extension idea that adds a proper "user exists"
  check before onboarding.

Run:
    python main.py
"""

import asyncio

from agent import build_agent
from memory import store_user_profile

# ── Example User Profile ──────────────────────────────────────────────────────
# This simulates a first-time onboarding step.
# In a real app this would come from a registration form or database.

DEMO_USER_ID = "user_42"

DEMO_USER_PROFILE = {
    "name": "Sarah",
    "calorie_goal": 1800,
    "restrictions": ["vegetarian"],
    "allergies": ["peanuts"],
    "goals": "lose 5kg, improve gut health",
}


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    """
    Application entry point.

    Steps:
      1. Compile the LangGraph agent (three nodes: recall → respond → remember).
      2. Store the demo user profile in Cognee so the agent has context from
         the very first message. (cognify() runs here — allow 5–15 s.)
      3. Enter the interactive chat loop, invoking the agent on every message.
    """

    # Step 1 — compile agent graph
    agent = build_agent()

    # Step 2 — onboard the demo user (writes profile + triggers cognify)
    print("⏳ Setting up user profile in Cognee (first run may take 5–15 s)…")
    await store_user_profile(DEMO_USER_ID, DEMO_USER_PROFILE)
    print("✅ Profile stored.\n")

    # Step 3 — interactive loop
    print("🥗 NutriAgent ready. Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()

        # Allow the user to exit gracefully.
        if user_input.lower() == "quit":
            print("👋 Goodbye! Your session has been saved to memory.")
            break

        # Skip accidental empty submissions.
        if not user_input:
            continue

        # Run the full recall → respond → remember pipeline.
        # All four keys must be present; memory_context and response
        # start empty and are filled by the graph nodes.
        result = await agent.ainvoke(
            {
                "user_id": DEMO_USER_ID,
                "user_message": user_input,
                "memory_context": "",
                "response": "",
            }
        )

        print(f"\n🤖 NutriAgent: {result['response']}\n")


if __name__ == "__main__":
    asyncio.run(main())

from google.adk.agents import Agent

layout_agent = Agent(
    name="LayoutAgent",
    model="gemini-2.5-flash-lite",
    description="Based on the brief and the recommended components for conversion, "
    + "creates a layout for a page by selecting the best components from the library.",
    instruction="Answer questions",
)

root_agent = layout_agent

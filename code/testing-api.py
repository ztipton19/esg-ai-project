from dotenv import load_dotenv
import os
import anthropic

# Load environment variables from .env file
load_dotenv()
api_key=os.getenv("ANTHROPIC_API_KEY")

if api_key:
    print(f"✓ API key loaded! (starts with: {api_key[:10]}...)")
else:
    print("✗ API key not found!")

DEVELOPMENT_MODE = True

# Initialize the client with your API key
client = anthropic.Anthropic(
    api_key=api_key
)

model = "claude-haiku-4-5-20251001" if DEVELOPMENT_MODE else "claude-sonnet-4-5-20250929"

# Send a message to Claude
message = client.messages.create(
    model=model,
    max_tokens=300,
    messages=[
        {"role": "user", "content": "Hello, Claude! I just learned how to connect to you through Positron IDE"}
    ]
)

# Access the response
response_text = message.content[0].text
print(response_text)

# Extract token usage
input_tokens = message.usage.input_tokens
output_tokens = message.usage.output_tokens

# Claude Sonnet 4.5 pricing (as of Dec 2025)
#input_cost_per_million = 3.00  # $3 per 1M input tokens
#output_cost_per_million = 15.00  # $15 per 1M output tokens

# Claude Haiku 4.5: $0.80 / $4.00 per million (input/output) - Cheapest
input_cost_per_million = 0.80
output_cost_per_million = 4.00

# Calculate cost
input_cost = (input_tokens / 1_000_000) * input_cost_per_million
output_cost = (output_tokens / 1_000_000) * output_cost_per_million
total_cost = input_cost + output_cost

print(f"Input tokens: {input_tokens}")
print(f"Output tokens: {output_tokens}")
print(f"Estimated cost: ${total_cost:.6f}")


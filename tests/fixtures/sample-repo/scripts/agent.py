import anthropic

client = anthropic.Anthropic()
client.messages.create(model="claude-opus-4-8", max_tokens=1000, messages=[])

# Set your OpenAI API key as an environment variable
export OPENAI_API_KEY="your-api-key-here"

# Or load from .env file (recommended)
# Create a .env file with: OPENAI_API_KEY=your-api-key-here

python scripts/generate_debates.py


You’ll get:

debates/debates.json

3) Plug into v0 UI (no API key needed)

Fastest path in Next.js:

Put debates.json into public/debates.json

Fetch it client-side:

const data = await fetch("/debates.json").then(r => r.json());


Render data.cases[i].
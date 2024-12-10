import anthropic


def stock_pitch(df, api_key):
    client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY") 
    api_key=api_key)

    if len(df) > 0:
        stock = df['symbol'].values[0]
        #get pitch for the first stock
        prompt = f"Write a 2-3 sentence pitch for the following stock symbol: {stock} , it should use the companies name, in the style of wallstreet bets."
    else:
        #Prommpt for no stocks to make money on today.
        prompt = "Write a 2-3 sentence message about how there is no oppertunity in the market today, in the style of wallstreets bets."

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt} ])

    return message.content[0].text


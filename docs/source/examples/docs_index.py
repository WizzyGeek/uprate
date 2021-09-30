import uprate as up

@up.ratelimit(1 / (up.Seconds(2) + up.Minutes(1)))
def oppressed():
    print("Hello World. I can only speank once every 62 seconds :(")

oppressed()

try:
    # Within 62 seconds
    oppressed()
except up.RateLimitError:
    print("I can't speak too fast ;(")

@up.ratelimit(1 / (up.Seconds(2) + up.Minutes(1)), on_retry=up.on_retry_block)
def rebellion():
    print("Hello World. I wait for my chance to speak")

rebellion()
rebellion() # blocks current thread for 62 seconds

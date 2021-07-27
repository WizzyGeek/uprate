<h1 align="center">
    <img src="https://github.com/WizzyGeek/WizzyGeek/raw/main/assets/uprate/uprate_logo_rev2.png">
</h1>

<div align="center">
    A fully typed, simple ratelimit library.
</div>

<div align="center">
    <br/>
    <img src="https://forthebadge.com/images/badges/made-with-python.svg">
    <img src="https://forthebadge.com/images/badges/built-with-love.svg">
</div>

<hr/>

> Note: The project is still in planning

# About

Uprate is a robust, simple ratelimit library.<br/>
While providing a simple to use api, it is also highly scalable
and provides absolute control for fine-tuning.<br/> Hence, Uprate
can be used in all stages of your app from prototyping to production! 🚀
<br/>
[Here](#example) is a simple example.

## Why?

There are two ways ratelimits are implemented in python
 - Make everything from scratch
 - Use a framework dependent ratelimit library.

The problem in the first way is obvious, it's harder, consumes more time.<br/>
Using a framework dependent ratelimit library is more feasible, but often
these libraries don't provide features like external stores, multiple ratelimits
and manual key specification. While there are some awesome ratelimit libraries for
framwork X, not everyone uses framework X 😕.

## [Documentation](https://uprate.readthedocs.io/en/latest/)

> The documentation is currently in development! Please stay tuned!

The documentation can be found at <https://uprate.readthedocs.io/en/latest/> <br/>

# Getting Started

## Installation

You can install the latest stable version from pypi by
```
pip install uprate
```
*or* you can install the dev version from github
```
pip install git+https://github.com/WizzyGeek/uprate.git@master#egg=uprate
```
## Usage

```
import uprate
```

And you are good to go! 🤘

## Example

> This example is not fully implemented, yet.

Here is a simple example that demonstrates Uprate's Awesomeness.

```py
import uprate

@uprate.ratelimit(1 / (uprate.Seconds(2) + uprate.Minutes(1)))
def limited():
    ...

limited()

try:
    # Within 62 seconds
    limited()
except uprate.RateLimitError:
    print("called function too fast")
```

And **so much more**!

<div align="center">
    <h1></h1>
    <h6>Thanks to <a href="https://github.com/someonetookmycode">@someonetookmycode</a> for the graphical assets</h6>
    <h6>© WizzyGeek 2021</h6>
</div>
